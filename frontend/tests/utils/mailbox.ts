import { createServer, type Server as HttpServer } from "node:http"
import {
  createServer as createSmtpServer,
  type Server as NetServer,
  type Socket,
} from "node:net"

const MAX_MESSAGE_BYTES = 2 * 1024 * 1024
const DEFAULT_HTTP_PORT = 1080
const DEFAULT_SMTP_PORT = 2525

export type MailboxEmail = {
  id: number
  recipients: string[]
  subject: string
}

type StoredEmail = MailboxEmail & { html: string }

function decodeTransfer(value: string, encoding: string | undefined) {
  if (encoding?.toLowerCase() === "base64") {
    return Buffer.from(value.replace(/\s/g, ""), "base64").toString("utf8")
  }
  if (encoding?.toLowerCase() === "quoted-printable") {
    return value
      .replace(/=\r?\n/g, "")
      .replace(/=([0-9a-f]{2})/gi, (_, hex: string) =>
        String.fromCharCode(Number.parseInt(hex, 16)),
      )
  }
  return value
}

function headersAndBody(raw: string) {
  const split = raw.search(/\r?\n\r?\n/)
  if (split < 0) return { headers: new Map<string, string>(), body: raw }
  const headerText = raw.slice(0, split)
  const body = raw.slice(split).replace(/^\r?\n\r?\n/, "")
  const headers = new Map<string, string>()
  for (const line of headerText.replace(/\r?\n[ \t]+/g, " ").split(/\r?\n/)) {
    const colon = line.indexOf(":")
    if (colon > 0)
      headers.set(
        line.slice(0, colon).toLowerCase(),
        line.slice(colon + 1).trim(),
      )
  }
  return { headers, body }
}

function decodeMimePart(raw: string): string | null {
  // ponytail: bounded MIME subset for this test client; use a real parser if mail formats broaden.
  const { headers, body } = headersAndBody(raw)
  const contentType = headers.get("content-type") ?? ""
  const transfer = headers.get("content-transfer-encoding")
  if (/multipart\//i.test(contentType)) {
    const boundary =
      contentType.match(/boundary\s*=\s*(?:"([^"]+)"|([^;\s]+))/i)?.[1] ??
      contentType.match(/boundary\s*=\s*([^;\s]+)/i)?.[1]
    if (!boundary) return null
    const parts = body
      .split(`--${boundary}`)
      .filter((part) => !/^--\s*$/.test(part.trim()))
    for (const part of parts) {
      const { headers: partHeaders } = headersAndBody(part)
      if (/text\/html/i.test(partHeaders.get("content-type") ?? "")) {
        return decodeTransfer(
          headersAndBody(part).body.trim(),
          partHeaders.get("content-transfer-encoding"),
        )
      }
      const nested = decodeMimePart(part)
      if (nested) return nested
    }
    return null
  }
  if (/text\/html/i.test(contentType) || !contentType)
    return decodeTransfer(body.trim(), transfer)
  return null
}

function parseMessage(raw: string, id: number): StoredEmail {
  const { headers } = headersAndBody(raw)
  const recipients = (headers.get("to") ?? "")
    .split(",")
    .map((recipient) => recipient.trim())
    .filter(Boolean)
  return {
    id,
    recipients,
    subject: headers.get("subject") ?? "",
    html: decodeMimePart(raw) ?? raw,
  }
}

function send(socket: Socket, value: string) {
  socket.write(`${value}\r\n`)
}

export async function startMailbox({
  httpPort = Number(process.env.E2E_MAILBOX_HTTP_PORT ?? DEFAULT_HTTP_PORT),
  smtpPort = Number(process.env.E2E_SMTP_PORT ?? DEFAULT_SMTP_PORT),
}: {
  httpPort?: number
  smtpPort?: number
} = {}) {
  const messages: StoredEmail[] = []
  let nextId = 1
  const http = createServer((request, response) => {
    const path = new URL(request.url ?? "/", "http://127.0.0.1").pathname
    if (request.method !== "GET") {
      response.writeHead(405).end()
      return
    }
    if (path === "/messages") {
      response.writeHead(200, { "content-type": "application/json" })
      response.end(
        JSON.stringify(messages.map(({ html: _html, ...email }) => email)),
      )
      return
    }
    const match = path.match(/^\/messages\/(\d+)\.html$/)
    const email = match
      ? messages.find((candidate) => candidate.id === Number(match[1]))
      : undefined
    if (!email) {
      response.writeHead(404).end("Not found")
      return
    }
    response.writeHead(200, { "content-type": "text/html; charset=utf-8" })
    response.end(email.html)
  })
  const smtp = createSmtpServer((socket) => {
    let data = ""
    let state: "command" | "data" = "command"
    send(socket, "220 e2e-mailbox ESMTP")
    socket.setEncoding("utf8")
    socket.on("data", (chunk: string) => {
      data += chunk
      if (Buffer.byteLength(data, "utf8") > MAX_MESSAGE_BYTES) {
        send(socket, "552 message exceeds test mailbox limit")
        socket.destroy()
        return
      }
      while (true) {
        if (state === "data") {
          const terminator = data.indexOf("\r\n.\r\n")
          if (terminator < 0) break
          messages.push(parseMessage(data.slice(0, terminator), nextId++))
          data = data.slice(terminator + 5)
          state = "command"
          send(socket, "250 2.0.0 queued")
          continue
        }
        const end = data.indexOf("\r\n")
        if (end < 0) break
        const line = data.slice(0, end)
        data = data.slice(end + 2)
        const command = line
          .slice(0, line.indexOf(" ") < 0 ? line.length : line.indexOf(" "))
          .toUpperCase()
        if (command === "EHLO" || command === "HELO")
          send(socket, "250-localhost\r\n250 OK")
        else if (command === "MAIL" || command === "RCPT")
          send(socket, "250 OK")
        else if (command === "DATA") {
          state = "data"
          send(socket, "354 End data with <CR><LF>.<CR><LF>")
        } else if (command === "RSET") send(socket, "250 OK")
        else if (command === "QUIT") {
          send(socket, "221 Bye")
          socket.end()
        } else send(socket, "250 OK")
      }
    })
  })
  await listen(http, httpPort)
  try {
    await listen(smtp, smtpPort)
  } catch (error) {
    await close(http)
    throw error
  }
  return {
    http,
    smtp,
    httpPort: (http.address() as { port: number }).port,
    smtpPort: (smtp.address() as { port: number }).port,
    close: async () => {
      await Promise.all([close(http), close(smtp)])
    },
  }
}

type Listener = HttpServer | NetServer

function listen(server: Listener, port: number) {
  return new Promise<void>((resolve, reject) => {
    server.once("error", reject)
    server.listen(port, "127.0.0.1", () => {
      server.removeListener("error", reject)
      resolve()
    })
  })
}

function close(server: Listener) {
  return new Promise<void>((resolve) => server.close(() => resolve()))
}

if (import.meta.main) {
  const mailbox = await startMailbox()
  process.stdout.write(
    `${JSON.stringify({ httpPort: mailbox.httpPort, smtpPort: mailbox.smtpPort })}\n`,
  )
  const stop = async () => {
    await mailbox.close()
    process.exit(0)
  }
  process.once("SIGTERM", stop)
  process.once("SIGINT", stop)
}
