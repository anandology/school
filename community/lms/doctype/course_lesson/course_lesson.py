# -*- coding: utf-8 -*-
# Copyright (c) 2021, FOSS United and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from ...md import markdown_to_html, find_macros

class CourseLesson(Document):
    def on_update(self):
        dynamic_documents = ["Exercise", "Quiz"]
        for section in dynamic_documents:
            self.update_lesson_name_in_document(section)

    def update_lesson_name_in_document(self, section):
        doctype_map= {
            "Exercise": "Exercise",
            "Quiz": "LMS Quiz"
        }
        macros = find_macros(self.body)
        documents = [value for name, value in macros if name == section]
        index = 1
        for name in documents:
            e = frappe.get_doc(doctype_map[section], name)
            e.lesson = self.name
            e.index_ = index
            e.save()
            index += 1
        self.update_orphan_documents(doctype_map[section], documents)

    def update_orphan_documents(self, doctype, documents):
        """Updates the documents that were previously part of this lesson,
        but not any more.
        """
        linked_documents = {row['name'] for row in frappe.get_all(doctype, {"lesson": self.name})}
        active_documents = set(documents)
        orphan_documents = linked_documents - active_documents
        for name in orphan_documents:
            ex = frappe.get_doc(doctype, name)
            ex.lesson = None
            ex.index_ = 0
            ex.index_label = ""
            ex.save()

    def render_html(self):
        print(self.body)
        return markdown_to_html(self.body)

    def get_exercises(self):
        if not self.body:
            return []

        macros = find_macros(self.body)
        exercises = [value for name, value in macros if name == "Exercise"]
        return [frappe.get_doc("Exercise", name) for name in exercises]

    def get_progress(self):
        return frappe.db.get_value("LMS Course Progress", {"lesson": self.name, "owner": frappe.session.user}, "status")

    def get_slugified_class(self):
        if self.get_progress():
            return ("").join([ s for s in self.get_progress().lower().split() ])
        return

@frappe.whitelist()
def save_progress(lesson, course, status):
    if not frappe.db.exists("LMS Batch Membership",
            {
                "member": frappe.session.user,
                "course": course
            }):
        return

    if frappe.db.exists("LMS Course Progress",
            {
                "lesson": lesson,
                "owner": frappe.session.user,
                "course": course
            }):
        doc = frappe.get_doc("LMS Course Progress",
                {
                    "lesson": lesson,
                    "owner": frappe.session.user,
                    "course": course
                })
        doc.status = status
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({
            "doctype": "LMS Course Progress",
            "lesson": lesson,
            "status": status,
        }).save(ignore_permissions=True)
    course_details = frappe.get_doc("LMS Course", course)
    return course_details.get_course_progress()
