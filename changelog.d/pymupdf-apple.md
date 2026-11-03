### Changed

- On a Mac with Apple silicon (M1 or later), PDFs are now read with
  PyMuPDF 2, as on Windows x64 and Linux, with Python 3.11 to 3.14.
  Intel Macs keep PyMuPDF 1.x. PyMuPDF 2 brings onnxruntime, whose
  packages need macOS 14 or later on such a Mac, so there the desktop
  extension needs macOS 14 or later: on macOS 13 or earlier the updated
  extension does not start, and 0.15.2's extension is the last that
  starts there. The first start after the update needs the internet and
  downloads up to about 105 MB of libraries for reading PDFs, where
  0.15.2 needed about 33 MB. Exegete switches onnxruntime's usage
  reports off there before it loads, as on Linux.
- On such a Mac, psutil comes with PyMuPDF 2, so the scan of running
  programs for signs of QualCoder goes through psutil rather than `ps`.
  The scan now reads a program whose path holds a space whole. It can
  no longer read the command lines of another account's programs, which
  macOS keeps from it: a program run through Python by another account
  on the same Mac is no longer among the signs of QualCoder, while an
  app is still recognised by its name, and the chat history's recent
  change is then still given as a sign.
- Installs from PyPI (pip, pipx, uv tool and uvx) on such a Mac choose
  the releases by the macOS release and the Python. macOS 14 or later
  takes PyMuPDF 2 with the newest onnxruntime. macOS 13 with Python 3.11
  to 3.13 takes onnxruntime 1.23.2, and macOS 11 or 12 with Python 3.11
  or 3.12 takes 1.19.2, older releases not tried with Exegete. On macOS
  13 with Python 3.14, and on macOS 11 or 12 with Python 3.13 or 3.14,
  the install stops before anything is installed or removed, and an
  update with pip or pipx that stops was seen to leave the install as
  it was. The Terminal guide gives the ways round.

### Documents

- INSTALL says what a Mac with Apple silicon needs: macOS 14 or later
  for the extension, where Anthropic's help page asks for macOS 13 or
  later for Claude Desktop itself. It also gives what the update fetches
  there, and what to do when the extension does not start on macOS 13
  or earlier. The README's one-click steps and the extension's
  description state the same floor. The Terminal guide, PRIVACY, TOOLS,
  CONTRIBUTING and NOTICE count Macs with Apple silicon among the
  computers on PyMuPDF 2.

### For contributors

- The optional part's second line adds Macs with Apple silicon
  (`sys_platform == 'darwin' and platform_machine == 'arm64'`), and the
  first line keeps every other computer. `uv.lock` adds the macOS
  packages these need, with no release moved. CI's dry run asks about
  that Mac at macOS 14.0, the table of what the extension installs
  expects PyMuPDF 2 there, and the tests hold each Mac's floor (14.0 on
  Apple silicon, 10.15 on Intel) and the texts that state it. CI's
  macOS jobs now run the suite with PyMuPDF 2, so the tests of
  onnxruntime and a home folder, and of the scan through psutil, run
  there too.
