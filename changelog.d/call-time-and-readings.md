### Changed

- **A call that brings in documents works for up to 50 seconds in the
  Claude Desktop extension**, where it worked for 30, before it leaves
  the rest for the next call: on the maintainer's computer on 17
  November 2026, Claude Desktop, whose chat and Cowork are now one
  conversation, stopped waiting for an extension's call after 80
  seconds, and the extension's time is set from that limit less 30
  seconds. Every other way of installing keeps 30 seconds, and
  `EXEGETE_CALL_SECONDS` still sets it on any route.

### Documents

- **Two readings checked again on 17 November 2026.** The Terminal
  guide gives Claude Desktop's limit as 80 seconds, where it gave 60
  seconds in Cowork and 4 minutes in the chat (measured on 19 October).
  INSTALL's "Going back to an earlier version" says that installing
  0.15.3 over 0.15.4 cleared the extension's settings, and so did
  installing 0.15.4 again over a test build of the same version.
