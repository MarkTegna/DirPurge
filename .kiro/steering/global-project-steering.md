# Project Standards

## Filename Format
- Use `YYYYMMDD-HH-MM` for all log and output filenames, where hours are in 24-hour format

## Platform
- All programs are developed for the Windows platform

## Programming Language
- Software should be written in Python

## Docker Standards
- All Docker containers must use Ubuntu 24.04 base images
- Use `ubuntu:24.04` as the base image for all Dockerfiles
- When using language-specific images, prefer Ubuntu 24.04 variants (e.g., `python:3.11-slim` should be replaced with Ubuntu 24.04 + Python installation)

## Configuration
- All configurable options must be placed in `.ini` files
- All default options must be placed in any autocreated ini files
- All available but non default options must be placed in any autocreated ini files commented out

## Distribution
- Package the project as a Windows executable, including all supporting files
- Make a zip of the project distribution with the version number in the filename
- additional Distribution is intended via GitHub

## Version Control
- Push the project to GitHub upon completion of version 1
- Repository: [https://github.com/MarkTegna](https://github.com/MarkTegna)

## Test File Organization
- Put all test files in a `test_files` directory
- Exclude test files from distribution to GitHub (add to .gitignore)

## Build Artifact Organization
- Put all build ZIP files in a subdirectory (e.g., `releases/` or `builds/`)
- Do not distribute build ZIP files in the main upload to GitHub
- Only use build ZIP files in the releases part of the GitHub update
- Add build ZIP directory to .gitignore to prevent accidental commits

## Documentation Requirements
In documentation and built-in help instructions, include:
- Author: "Mark Oldham"
- Version number and compile date