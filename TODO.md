# TODOs

* implement a "findus-launcher" that handles all the common things, like command line parsing, database setup and so on. The user should only provide the handles for classification, and the contents of the glitching loop.
* Reduce dependencies even more
* remove numpy dependency
* Enum class GlitchState is complicated. Use bytes instead (b'error: rdp active' etc.)
* re-work findus/__init__.py: can a flat import hierarchy be achieved?