from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from unittest.mock import patch


class DadDagViewTests(TestCase):
    def test_pending_reviews_are_rendered_for_user_choice(self):
        user = get_user_model().objects.create_user(username="tester", password="secret")
        self.client.force_login(user)
        pta_file = SimpleUploadedFile(
            "pta.xlsx",
            b"dummy",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        zip_file = SimpleUploadedFile("fscfai.zip", b"PK", content_type="application/zip")

        fake_results = {
            "auto_updates": [],
            "pending_reviews": [
                {
                    "item_id": "item-1",
                    "xml_file": "sample.list",
                    "current_ref": "1234567890",
                    "current_ref_description": "Current description",
                    "old_xml_path": "C:/old/1234567890",
                    "candidates": [
                        {"value": "1111111111", "description": "Candidate A description", "score": 100},
                        {"value": "2222222222", "description": "Candidate B description", "score": 95},
                    ],
                    "automated_choice": "1111111111",
                }
            ],
            "updated_refs": [],
        }

        with patch("Listes_Types.DAD_DAG.views.Orchestrator") as orchestrator_cls:
            orchestrator_cls.return_value.process_all.return_value = (fake_results, None)
            response = self.client.post(
                reverse("dad_dag"),
                {"pta_file": pta_file, "zipped_fscfai": zip_file},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Listes_Types/DAD_DAG/audit_review.html")
        self.assertContains(response, "sample.list")
        self.assertContains(response, "1234567890")
        self.assertContains(response, "Candidate A description")

    def test_finalize_renders_successfully_without_results_table(self):
        user = get_user_model().objects.create_user(username="tester", password="secret")
        self.client.force_login(user)
        session = self.client.session
        session["dad_dag_reviews"] = [
            {
                "item_id": "item-1",
                "xml_file": "sample.list",
                "xml_path": "C:/temp/sample.list",
                "current_ref": "1234567890",
                "current_ref_description": "Current description",
                "old_xml_path": "C:/old/1234567890",
                "candidates": [],
            }
        ]
        session["dad_dag_auto_updates"] = [
            {
                "current_ref": "9876543210",
                "new_ref": "1111111111",
                "xml_path": "C:/temp/sample.list",
                "old_xml_path": "C:/old/9876543210",
            }
        ]
        session.save()

        with patch("Listes_Types.DAD_DAG.views.xml_parser") as mock_parser:
            mock_parser.return_value.update_reference.return_value = (False, "")
            mock_parser.return_value.save_versioned_file.return_value = None
            response = self.client.post(reverse("dad_dag_finalize"), {"choice_item-1": "1111111111"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Review completed")
        self.assertContains(response, "Auto-Updated References")
