#!/usr/bin/env python

"""
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
"""

import re
import datetime
import operator
import itertools
import functools

class WorkItem(object):
    """Base class of both complete and incomplete work items; corresponds to a single line in a todo.txt file."""

    project_context_re = re.compile("[@+]\S*\w")

    def __init__(self, line, text, inProgress, start = None):
        """Construct a WorkItem; should not be called directly.

        line - line number of item
        text - full text of line
        inProgress - complete or incomplete
        start - optional start date as text
        """

        self._line = line
        self._inProgress = inProgress
        self._start = start
        self._origText = text
        self._text = WorkItem.project_context_re.sub("", self._origText).strip()
        self._projectsContexts = map(str.strip, WorkItem.project_context_re.findall(self._origText))
        if self._start:
            self._startDate = datetime.datetime.strptime(self._start, "%Y-%m-%d").date()
        else:
            self._startDate = None

    def change_line(self, newLine):
        """Change the line number of this work item."""

        self._line = newLine
    
    @property
    def line(self):
        """The line number of this work item."""

        return self._line

    @property
    def in_progress(self):
        """Is this item in progress or not?"""

        return self._inProgress

    @property
    def start(self):
        """Start date, as text."""

        return self._start

    @property
    def orig_text(self):
        """Full original text of the item."""

        return self._origText

    @property
    def text(self):
        """Only the descriptive part of the text; no date, priority, projects or contexts."""

        return self._text

    @property
    def projects_contexts(self):
        """Sequence of all projects and contexts for this item."""
        
        return self._projectsContexts
    
    @property
    def projects(self):
        """Sequence of all the projects for this item."""

        return itertools.ifilter(operator.methodcaller('startswith', '@'), self._projectsContexts)
        
    @property
    def contexts(self):
        """Sequence of all the contexts for this item."""

        return itertools.ifilter(operator.methodcaller('startswith', '+'), self._projectsContexts)

class InProgressItem(WorkItem):
    """A work item that is not yet complete."""

    def __init__(self, line, text, priority = None, start = None):
        """Construct an in-progress work item.

        line - line number of item
        text - full text of line
        priority - optional text priority as a single character
        start - optional start date as text
        """

        WorkItem.__init__(self, line, text, True, start)
        self._priority = priority

    def __str__(self):
        ret = ""
        if self._priority:
            ret = "(%s) " % self._priority
        if self._start:
            ret = "%s%s " % (ret, self._start)
        ret = "%s%s" % (ret, self._origText)
        return ret.strip()

    def add_to_file(self, destFile):
        """Adds itself to an existing TodoFile as an in-progress item."""

        destFile.addExistingItem(self, False)
    
    @property
    def priority(self):
        """Priority as a single character."""

        return self._priority

    @property
    def priority_sort(self):
        """Priority used for sorting; an item with no priority will report 'ZZ' here and sort at the end."""

        if self._priority:
            return self._priority
        else:
            return "ZZ"

    @property
    def days_since_start(self):
        """Days since the start date of this item, or None if start date is not avaiable."""

        if self._startDate:
            return (datetime.date.today() - self._startDate).days
        else:
            return None

class CompleteItem(WorkItem):
    """A work item that has been completed."""

    def __init__(self, line, text, end, start = None):
        """Construct a complete work item.

        line - line number of item
        text - full text of line
        end - end date as text
        start - optional start date as text
        """

        WorkItem.__init__(self, line, text, False, start)
        self._end = end
        if self._end:
            self._endDate = datetime.datetime.strptime(self._end, "%Y-%m-%d").date()
        else:
            self._endDate = None

    def __str__(self):
        ret = "x %s " % self._end
        if self._start:
            ret = "%s%s " % (ret, self._start)
        ret = "%s%s" % (ret, self._origText)
        return ret.strip()
        
    def add_to_file(self, destFile):
        """Adds itself to an existing TodoFile as a complete item."""

        destFile.addExistingItem(self, True)
    
    @property
    def end(self):
        """End date, as text."""

        return self._end
    
    @property
    def days_taken(self):
        """Count of days taken to complete the item, if start date is available; otherwise None."""

        if self._startDate and self._endDate:
            return (self._endDate - self._startDate).days
        else:
            return None

class TodoFile(object):
    """Class representing a complete todo file, built from the file data."""

    incomplete_re = re.compile("(?P<priority>\([A-Z]\) )?(?P<start>[0-9]{4}-[0-9]{2}-[0-9]{2} )?(?P<text>.+)")
    complete_re = re.compile("x (?P<end>[0-9]{4}-[0-9]{2}-[0-9]{2} )(?P<start>[0-9]{4}-[0-9]{2}-[0-9]{2} )?(?P<text>.+)")

    def __init__(self, filedata):
        """Construct a TodoFile.

        filedata - the full text of the todo.txt file
        """

        lines = filedata.splitlines()

        self._incomplete_items = dict()
        self._complete_items = dict()
        self._next_line = len(lines)

        for i in range(len(lines)):
            line = lines[i]

            mo = TodoFile.complete_re.match(line)
            if mo:
                start = mo.group('start')
                if start:
                    start = start.strip()
                end = mo.group('end')
                if end:
                    end = end.strip()
                item = CompleteItem(i, mo.group('text'), end, start)
                self._complete_items[i] = item
                continue

            mo = TodoFile.incomplete_re.match(line)
            if mo:
                priority = mo.group('priority')
                if priority:
                    priority = priority.strip('() ')
                start = mo.group('start')
                if start:
                    start = start.strip()
                item = InProgressItem(i, mo.group('text'), priority, start)
                self._incomplete_items[i] = item
                continue

    def get_complete_items(self, key):
        """All completed items, sorted by the provided key (usually an attrgetter)."""

        return sorted(self._complete_items.itervalues(), key=key)

    def get_incomplete_items(self, key):
        """All incomplete items, sorted by the provided key (usually an attrgetter)."""

        return sorted(self._incomplete_items.itervalues(), key=key)
    
    def add_existing_item(self, item, complete):
        """Adds an existing WorkItem to this file on the next available line.

        item - the WorkItem to add
        complete - is this WorkItem complete or not
        """

        item.change_line(self._next_line)
        
        if complete:
            self._complete_items[self._next_line] = item
        else:
            self._incomplete_items[self._next_line] = item
        self._next_line = self._next_line + 1

    def add_item(self, text, priority, start, projects, contexts):
        """Adds a new item to this file.

        text - descriptive text for the item
        priority - single character priority
        start - start date as text
        projects - sequence of projects
        contexts - sequence of contexts
        """

        full_text =  text + " " + " ".join(('+' + proj for proj in projects)) + " " + " ".join(('@' + con for con in contexts))
        item = InProgressItem(self._next_line, full_text, priority, start)
        self._incomplete_items[self._next_line] = item
        self._next_line = self._next_line + 1

    def edit_item(self, line, text, priority, projects, contexts):
        """Edits an existing item in this file.

        line - line number to edit
        text - descriptive text for the item
        priority - single character priority
        projects - sequence of projects
        contexts - sequence of contexts
        """

        full_text =  text + " " + " ".join(('+' + proj for proj in projects)) + " " + " ".join(('@' + con for con in contexts))
        orig_item = self.get_item(line)
        item = InProgressItem(line, full_text, priority, orig_item.start)
        self._incomplete_items[line] = item

    def complete_item(self, line, when):
        """Marks an item as complete.

        line - line number to complete
        when - end date for the complete item
        """

        if line not in self._incomplete_items:
            return

        prev_item = self._incomplete_items[line]
        new_item = CompleteItem(line, prev_item.origText, when, prev_item.start)

        del self._incomplete_items[line]
        self._complete_items[line] = new_item
        
    def move_item(self, line, dest_file):
        """Moves an item to a different TodoFile.

        line - line number to move
        destFile - TodoFile to move to
        """

        if line not in self._incomplete_items and line not in self._complete_items:
            return
        
        item = self.get_item(line)
        
        item.add_to_file(dest_file)
        self.remove_line(line)
    
    def archive_item(self, line, dest_file):
        """Archives a complete item to a different TodoFile.

        line - line number to archive; must be a complete item
        destFile - TodoFile to archive to
        """

        if line not in self._complete_items:
            return
        
        self.move_item(line, dest_file)
    
    def archive_all_items(self, dest_file):
        """Archive all complete items in this file to a different TodoFile."""

        for line in self._complete_items.iterkeys():
            self.archive_item(line, dest_file)

    def remove_line(self, line):
        """Remove a line from this TodoFile, shifting all other lines to compensate."""

        bottom_incomplete_items = { l: item for l, item in self._incomplete_items.items() if l < line }
        top_incomplete_items = { l - 1: item for l, item in self._incomplete_items.items() if l > line }
        bottom_incomplete_items.update(top_incomplete_items)

        bottom_complete_items = { l: item for l, item in self._complete_items.items() if l < line }
        top_complete_items = { l - 1: item for l, item in self._complete_items.items() if l > line }
        bottom_complete_items.update(top_complete_items)

        self._incomplete_items = bottom_incomplete_items
        self._complete_items = bottom_complete_items

    def get_item(self, line):
        """Get the item at a specified line number."""

        if line in self._incomplete_items:
            return self._incomplete_items[line]
        elif line in self._complete_items:
            return self._complete_items[line]
        else:
            return None

    def get_all_projects(self):
        """Get all the unique projects mentioned by items in this file."""

        return self._get_projects_or_contexts('+')

    def get_all_contexts(self):
        """Get all the unique contexts mentioned by items in this file."""

        return self._get_projects_or_contexts('@')

    def _get_projects_or_contexts(self, starts_with):
        # chain the complete and incomplete items
        # then form a list of lists, where the sublists are the projects and contexts for each item
        # flatten that to a single list (works with reduce since it's known to be only one level deep)
        # form a set to eliminate duplicates
        # filter to only things that match the prefix
        # then return it sorted
        return sorted(
                itertools.ifilter(operator.methodcaller('startswith', starts_with),
                    set(
                        functools.reduce(operator.concat,
                            map(operator.attrgetter('projects_contexts'), itertools.chain(self._incomplete_items.itervalues(), self._complete_items.itervalues()))))))

    def __str__(self):
        ret = ""
    
        max_line = self._next_line
        for i in range(0, max_line):
            if i in self._incomplete_items:
                item = self._incomplete_items[i]
            elif i in self._complete_items:
                item = self._complete_items[i]
            else:
                item = ""
            ret = "%s%s\n" % (ret, str(item))

        return ret

if __name__ == "__main__":
    import fileinput

    data = ""
    name = ""
    for line in fileinput.input():
        if fileinput.isfirstline() and data != "":
            print "Parse of %s:" % (name)
            tf = TodoFile(data)
            print "%s" % (str(tf))
            data = ""
        data = data + line
        name = fileinput.filename()

    print "Parse of %s:" % (name)
    tf = TodoFile(data)
    print "%s" % (str(tf))
