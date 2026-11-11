### For contributors

- **A test of the workspace copy that failed on Windows.** It compared
  the original project's entries before and after a copy, with each
  entry's times read from a folder listing. On Windows a listing gives
  a folder's times from its parent's index, which is updated later, so
  two listings could differ where nothing had changed. The test now
  reads each entry's own times.
