
==============
todo_parser.py
==============

A module for converting files in the `todo.txt format <http://todotxt.com/>`_ to Python objects that allow
in-memory editing operations on the representation; these objects can regenerate the contents of the file,
allowing for round-trip editing.

Dependencies
============

None apart from Python; tested on 2.7.1.

Usage
=====

Command Line
------------

When run from the command line this module should simply parse any files given (or stdin) and print them
out after round-tripping them. This is present purely for easy verification of the parse correctness.

Code
----

Simply instantiate a TodoFile object from your file data::

    tf = TodoFile(filedata)

Then modify it as desired::

    tf.complete_item(5)

When finished, the new representation can be retrieved by string conversion::

    dest.write(str(tf))

To work with two files (e.g. for archiving)::

    src_file = TodoFile(src_data)
    dest_file = TodoFile(dest_data)

    src_file.move_item(3, dest_file)
    src_file.archive_all_items(dest_file)

    src.write(str(src_file))
    dest.write(str(dest_file))

Contributing
============

If you use and like this, please let me know! Patches, pull requests, suggestions etc. are all gratefully
accepted.

License
=======

Copyright 2012 Benedict Singer

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

