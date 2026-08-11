import { stopMailbox } from "./mailbox.setup"

export default async function globalTeardown() {
  await stopMailbox()
}
