# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2023-04-01

### Changed

- App won't crash now when disconnecting and reconnecting the tapo c-200 cam. 
- Set logging to false as default.
- Added logging to published topics

## [1.0.5] - 2023-04-01

### Changed

- get token every minute instead of 30 minutes for testing.
- improved logging

## [1.0.4] - 2023-04-01

### Added

- changelog

## [1.0.3] - 2023-04-01

### Added

- Logging is switchable by addon settings (default: on, options: on / off, type: bool)
- "token-timer" only resets if token request was successful now, still WIP. Now you shouldn't have to wait up to half an hour for the cam to connect
- adding logging for further development. To implement basic logging for mqtt and request "events" so users can see whats not working