### Security

- **CI's validator.** The official validator's lock moves node-forge
  from 1.4.0 to 1.4.1, a release that none of the twelve advisories
  on node-forge affects, so the advisory check no longer needs to
  accept them. node-forge is a library of the validator that CI alone
  installs to check the extension's manifest, and Exegete installs none
  of it.
