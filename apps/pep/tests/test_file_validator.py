from django.test import SimpleTestCase

from apps.pep.exceptions import (
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from apps.pep.services.file_validator import (
    validate_upload_metadata,
)


class FileValidatorTests(SimpleTestCase):
    def test_accepts_valid_pdf(self) -> None:
        validate_upload_metadata(
            filename="document.pdf",
            file_size=1024,
            max_upload_mb=10,
        )

    def test_accepts_valid_docx(self) -> None:
        validate_upload_metadata(
            filename="document.DOCX",
            file_size=1024,
            max_upload_mb=10,
        )

    def test_rejects_invalid_extension(self) -> None:
        with self.assertRaises(
            UnsupportedFileTypeError,
        ):
            validate_upload_metadata(
                filename="document.txt",
                file_size=1024,
                max_upload_mb=10,
            )

    def test_rejects_empty_file(self) -> None:
        with self.assertRaises(
            EmptyFileError,
        ):
            validate_upload_metadata(
                filename="document.pdf",
                file_size=0,
                max_upload_mb=10,
            )

    def test_rejects_large_file(self) -> None:
        with self.assertRaises(
            FileTooLargeError,
        ):
            validate_upload_metadata(
                filename="document.pdf",
                file_size=11 * 1024 * 1024,
                max_upload_mb=10,
            )
