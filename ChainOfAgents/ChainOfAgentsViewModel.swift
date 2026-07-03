//
//  ChainOfAgentsViewModel.swift
//  ChainOfAgents
//
//  Created by Rudrank Riyam on 1/28/25.
//

import PDFKit
import SwiftUI
import UniformTypeIdentifiers

@MainActor
final class ChainOfAgentsViewModel: ObservableObject {
    @Published var selectedPDFURL: URL?
    @Published var query = ""
    @Published var isLoading = false
    @Published var error: String?
    @Published var workerMessages: [WorkerMessage] = []
    @Published var managerMessage: String = ""
    @Published var pageCount: Int = 0
    @Published var totalChunks: Int = 0
    @Published var useOnDeviceProcessing = false

    let llmManager = LLMManager()
    private let chunkSize = 2000
    private var urlComponents: URLComponents = {
        var components = URLComponents()
        components.scheme = "http"
        components.host = "localhost"
        components.port = 8000
        components.path = "/process-stream"
        return components
    }()

    init() {
        // Remove server check on init if on-device processing is selected
        Task { [weak self] in
            guard let self else { return }
            if !self.useOnDeviceProcessing {
                await self.checkServerStatus()
            }
        }
    }

    /// URL currently holding security-scoped access, so every successful
    /// startAccessingSecurityScopedResource() is balanced by a stop call.
    private var securityScopedURL: URL?

    func selectPDF(url: URL) {
        // Start accessing the security-scoped resource
        guard url.startAccessingSecurityScopedResource() else {
            error = "Permission denied to access the file"
            return
        }

        // Try to create PDFDocument to verify it's a valid PDF
        if let pdfDocument = PDFDocument(url: url) {
            // Release access held for any previously selected file before
            // keeping access open for the new one (needed later for reading).
            releaseSecurityScopedAccess()
            securityScopedURL = url
            selectedPDFURL = url
            pageCount = pdfDocument.pageCount
            error = nil
        } else {
            // Balance the successful start call on this failure path
            url.stopAccessingSecurityScopedResource()
            error = "Could not open PDF file"
        }
    }

    private func releaseSecurityScopedAccess() {
        securityScopedURL?.stopAccessingSecurityScopedResource()
        securityScopedURL = nil
    }

    func processText() {
        guard let pdfURL = selectedPDFURL else {
            error = "Please select a PDF file first"
            return
        }

        guard !query.isEmpty else {
            error = "Please provide a query"
            return
        }

        Task { [weak self] in
            guard let self else { return }
            self.isLoading = true
            self.error = nil
            self.workerMessages.removeAll()
            self.managerMessage = ""

            if self.useOnDeviceProcessing {
                await self.processOnDevice(pdfURL: pdfURL)
            } else {
                // Check server only when not using on-device processing
                if await self.isServerAvailable() {
                    await self.processWithServer(pdfURL: pdfURL)
                } else {
                    self.error = "Server not available. Please make sure the API server is running."
                }
            }

            self.isLoading = false
        }
    }

    private func processOnDevice(pdfURL: URL) async {
          guard let pdfDocument = PDFDocument(url: pdfURL) else {
              error = "Could not open PDF file"
              return
          }

          let text = ChainUtils.extractText(from: pdfDocument)
          let chunks = ChainUtils.splitIntoChunks(text: text, chunkSize: chunkSize)
          totalChunks = chunks.count

          var workerResponses: [String] = []
          var managerContext: String = "" // Manager maintains a summary

          for (index, chunk) in chunks.enumerated() {
              do {
                  // Worker processes chunk with context from manager
                  let response = try await llmManager.processChunk(
                      chunk,
                      query: query,
                      previousCU: managerContext
                  )

                  let workerMessage = WorkerMessage(
                      id: index + 1,
                      message: response,
                      progress: StreamMessage.ProgressInfo(
                          current: index + 1,
                          total: totalChunks
                      )
                  )

                  workerMessages.append(workerMessage)
                  workerResponses.append(response)

                  // Manager updates context based on worker output
                  managerMessage = try await llmManager.updateContext(
                      managerContext: managerContext,
                      workerResponse: response,
                      query: query
                  )
              } catch {
                  self.error = "Error processing chunk \(index + 1): \(error.localizedDescription)"
                  return
              }
          }
      }

    private func processWithServer(pdfURL: URL) async {
        guard let url = urlComponents.url else {
            error = "Invalid URL configuration"
            return
        }

        do {
            // Read PDF data
            let pdfData = try Data(contentsOf: pdfURL)

            // Create multipart form data
            let boundary = UUID().uuidString
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue(
                "multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
            request.setValue("text/event-stream", forHTTPHeaderField: "Accept")

            // Create body
            var data = Data()
            data.append("\r\n--\(boundary)\r\n".data(using: .utf8)!)
            data.append(
                "Content-Disposition: form-data; name=\"pdf\"; filename=\"\(pdfURL.lastPathComponent)\"\r\n"
                    .data(using: .utf8)!)
            data.append("Content-Type: application/pdf\r\n\r\n".data(using: .utf8)!)
            data.append(pdfData)
            data.append("\r\n--\(boundary)\r\n".data(using: .utf8)!)
            data.append("Content-Disposition: form-data; name=\"query\"\r\n\r\n".data(using: .utf8)!)
            data.append(query.data(using: .utf8)!)
            data.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

            request.httpBody = data

            let (stream, response) = try await URLSession.shared.bytes(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw NetworkError.invalidResponse
            }

            guard httpResponse.statusCode == 200 else {
                throw NetworkError.serverError(statusCode: httpResponse.statusCode)
            }

            var currentData = Data()

            for try await byte in stream {
                currentData.append(byte)

                if let str = String(data: currentData, encoding: .utf8),
                   str.contains("\n")
                {
                    // Split on newlines, but keep the trailing fragment (an
                    // incomplete line) in the buffer for the next iteration.
                    var lines = str.components(separatedBy: "\n")
                    let remainder = lines.removeLast()

                    for message in lines where !message.isEmpty {
                        if let sseMessage = SSEMessage(rawMessage: String(message)) {
                            let streamMessage = sseMessage.data

                            switch streamMessage.type {
                            case .metadata:
                                if let metadataContent = streamMessage.content.data(using: .utf8),
                                   let metadata = try? JSONDecoder().decode(
                                    MetadataMessage.self, from: metadataContent)
                                {
                                    totalChunks = metadata.total_chunks
                                }
                            case .worker:
                                workerMessages.append(
                                    WorkerMessage(
                                        id: workerMessages.count + 1,
                                        message: streamMessage.content,
                                        progress: streamMessage.progress
                                    ))
                            case .manager:
                                managerMessage = streamMessage.content
                            }

                        } else {
                            print("Failed to decode SSE message")
                        }
                    }

                    currentData = remainder.data(using: .utf8) ?? Data()
                }
            }

        } catch NetworkError.serverError(let statusCode) {
            self.error = "Server error: \(statusCode)"
        } catch NetworkError.invalidResponse {
            self.error = "Invalid response from server"
        } catch let error as URLError {
            switch error.code {
            case .cannotFindHost:
                self.error = "Cannot connect to server. Make sure the API server is running."
            case .networkConnectionLost:
                self.error = "Network connection lost. Please try again."
            case .notConnectedToInternet:
                self.error = "No internet connection available."
            default:
                self.error = "Network error: \(error.localizedDescription)"
            }
        } catch {
            self.error = "Error reading PDF: \(error.localizedDescription)"
        }
    }

    private func checkServerStatus() async {
        guard let url = URL(string: "http://localhost:8000/health") else { return }

        do {
            let (_, response) = try await URLSession.shared.data(from: url)
            if let httpResponse = response as? HTTPURLResponse {
                if httpResponse.statusCode != 200 {
                    await MainActor.run {
                        self.error = "Server is not responding correctly"
                    }
                }
            }
        } catch {
            await MainActor.run {
                self.error = "Server not available. Please make sure the API server is running."
            }
        }
    }

    // Add server availability check
    private func isServerAvailable() async -> Bool {
        guard let url = URL(string: "http://localhost:8000/health") else { return false }
        do {
            let (_, response) = try await URLSession.shared.data(from: url)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }
}

// MARK: - Models
enum MessageType: String, Codable {
    case metadata
    case worker
    case manager
}

struct ProcessRequest: Codable {
    let text: String
    let query: String
}

struct StreamMessage: Codable {
    let type: MessageType
    let content: String
    let progress: ProgressInfo?

    struct ProgressInfo: Codable {
        let current: Int
        let total: Int
    }
}

struct MetadataMessage: Codable {
    let total_chunks: Int
    let total_pages: Int
}

struct WorkerMessage: Identifiable {
    let id: Int
    let message: String
    let progress: StreamMessage.ProgressInfo?
}

// MARK: - Errors
enum NetworkError: Error {
    case invalidResponse
    case serverError(statusCode: Int)
}

// Add this helper struct to parse SSE messages
private struct SSEMessage {
    let data: StreamMessage

    init?(rawMessage: String) {
        guard rawMessage.hasPrefix("data: "),
              let jsonString = String(rawMessage.dropFirst(6)).data(using: .utf8),
              let message = try? JSONDecoder().decode(StreamMessage.self, from: jsonString)
        else {
            return nil
        }
        self.data = message
    }
}
