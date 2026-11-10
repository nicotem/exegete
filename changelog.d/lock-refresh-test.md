### For contributors

- **A lock test that failed at random on Windows.** The test of the
  lock's refresh on a full disk read the lock's lines before making
  its writes fail, so a refresh in between could change them. It now
  reads them while holding the lock's own mutex, under which every
  refresh writes.
