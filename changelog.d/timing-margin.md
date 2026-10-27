### For contributors

- **Two timing tests allow for the platform**, and still fail on what
  they are there to catch. The test that the count of names left in a
  file's text costs a small multiple of one plain pass of the
  detector's pattern now allows twelve times that pass, where it
  allowed five: Windows with Python 3.11 read 5.4 and 5.6, and a count
  that matches with one capture group per surface form, the slow shape
  the test guards against, reads about 26 on macOS with Python 3.13.
  The test of the lock file's format accepts a time up to a hundredth
  of a second ahead of the clock: the lock writes the time rounded to
  six decimals, and on Windows before Python 3.13 the clock moves in
  steps of 15.6 ms, so a current lock read in the same step can be a
  fraction of a microsecond ahead.
