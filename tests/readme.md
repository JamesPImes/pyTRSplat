# Unit Tests

For the image comparison, the maintainer must first run all the generating
functions and manually examine the results to see if they are behaving
correctly. They are saved to
`.\tests\_resources\expected_images\<relevant dir per class>`

From the root directory of the repository, call:

```commandline
(.venv) <...>\py -m tests.gen_all_test_classes
```

From then, the unit tests will compare the outputs against those manually
approved test results.

If `pytrsplat` is modified in any way that changes the output of any
platting class, the maintainer must rerun the comparison images. Any
outputs that are unchanged will not be overwritten.

## Platform-specific results

Linux outputs slightly different images than Windows or Mac (the font
rendering is slightly different). *__That being the case, the above process
must be completed twice: Once on either Windows or Mac, and again on Linux.__*
