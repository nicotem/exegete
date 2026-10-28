### Fixed

- **One Ctrl+C stops Exegete started by hand in a terminal**, as
  INSTALL, QUICKSTART and Exegete's own note say. Exegete prints one
  line, `Stopped by Ctrl+C`. Before, it kept running until Enter was
  pressed or the terminal was closed, and a second Ctrl+C printed an
  error report from Python. An interrupt can also reach Exegete while
  an app is using it, sent by the app or by a Ctrl+C in a terminal the
  two share. A change Exegete is making at that moment is finished
  first, but the app may not receive Exegete's answer, so the assistant
  may not know that the change was made. Before asking for the same
  change again, you could look at the project to see whether it is
  there. Nothing changes for an app that stops Exegete by closing its
  input or ending the process.
