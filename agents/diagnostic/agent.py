import json
import re
from pathlib import Path

import pdfplumber

from agents.document.llm import get_llm

from .prompts import DIAGNOSTIC_PROMPT
from .schemas import DiagnosticOutput


class DiagnosticAgent:
    """
    Symptom -> relevant OTHER assemblies.

    The Diagnostic Agent deliberately does NOT scan the
    complete catalogue.

    It reads only the first MAX_INDEX_PAGES pages, where
    the catalogue index / contents and assembly list are
    normally located.
    """

    MAX_INDEX_PAGES = 20

    def __init__(self):

        self.llm = get_llm()

    # ========================================================
    # EXTRACT FIRST 20 PAGES
    # ========================================================

    @classmethod
    def _extract_catalogue_text(
        cls,
        pdf_path,
    ):

        path = Path(pdf_path)

        if not path.exists():

            raise FileNotFoundError(
                f"Catalogue not found: {path}"
            )

        pages = []

        with pdfplumber.open(path) as pdf:

            page_count = min(
                len(pdf.pages),
                cls.MAX_INDEX_PAGES,
            )

            for page_number in range(
                1,
                page_count + 1,
            ):

                page = pdf.pages[
                    page_number - 1
                ]

                text = (
                    page.extract_text()
                    or ""
                )

                if text.strip():

                    pages.append(
                        f"PAGE {page_number}\n{text}"
                    )

        return "\n\n".join(pages)

    # ========================================================
    # NORMALISE
    # ========================================================

    @staticmethod
    def _normalise(text):

        return re.sub(
            r"[^a-z0-9]+",
            " ",
            str(text).lower(),
        ).strip()

    # ========================================================
    # RESPONSE → TEXT
    # ========================================================

    @staticmethod
    def _response_to_text(response):

        content = getattr(
            response,
            "content",
            response,
        )

        if isinstance(
            content,
            list,
        ):

            pieces = []

            for block in content:

                if isinstance(
                    block,
                    str,
                ):

                    pieces.append(
                        block
                    )

                elif (
                    isinstance(
                        block,
                        dict,
                    )
                    and "text"
                    in block
                ):

                    pieces.append(
                        str(
                            block["text"]
                        )
                    )

            return "\n".join(
                pieces
            ).strip()

        return str(
            content
        ).strip()

    # ========================================================
    # ROBUST JSON PARSER
    # ========================================================

    @classmethod
    def _parse_json(
        cls,
        content,
    ):

        content = (
            cls._response_to_text(
                content
            )
        )

        if not content:

            raise ValueError(
                "Diagnostic Agent returned "
                "an empty response."
            )

        # ----------------------------------------------------
        # Remove markdown fences
        # ----------------------------------------------------

        content = re.sub(
            r"```(?:json)?",
            "",
            content,
            flags=re.IGNORECASE,
        )

        content = (
            content
            .replace(
                "```",
                "",
            )
            .strip()
        )

        # ----------------------------------------------------
        # Normal JSON
        # ----------------------------------------------------

        try:

            parsed = json.loads(
                content
            )

            # Sometimes the model returns
            # JSON encoded as a string.

            if isinstance(
                parsed,
                str,
            ):

                parsed = json.loads(
                    parsed
                )

            if isinstance(
                parsed,
                dict,
            ):

                return parsed

        except Exception:
            pass

        # ----------------------------------------------------
        # JSON surrounded by text
        # ----------------------------------------------------

        start = content.find(
            "{"
        )

        end = content.rfind(
            "}"
        )

        if (
            start != -1
            and end > start
        ):

            candidate = (
                content[
                    start:end + 1
                ]
            )

            try:

                parsed = json.loads(
                    candidate
                )

                if isinstance(
                    parsed,
                    dict,
                ):

                    return parsed

            except Exception:
                pass

        # ----------------------------------------------------
        # Escaped JSON
        # ----------------------------------------------------

        cleaned = (
            content
            .replace(
                "\\n",
                "\n",
            )
            .replace(
                '\\"',
                '"',
            )
            .replace(
                "\\'",
                "'",
            )
        )

        start = cleaned.find(
            "{"
        )

        end = cleaned.rfind(
            "}"
        )

        if (
            start != -1
            and end > start
        ):

            try:

                parsed = json.loads(
                    cleaned[
                        start:end + 1
                    ]
                )

                if isinstance(
                    parsed,
                    dict,
                ):

                    return parsed

            except Exception:
                pass

        # ----------------------------------------------------
        # Last-resort extraction
        # ----------------------------------------------------

        match = re.search(
            r'"assemblies_to_check"\s*:\s*\[(.*?)\]',
            cleaned,
            flags=re.DOTALL,
        )

        if match:

            values = re.findall(
                r'"([^"]+)"',
                match.group(1),
            )

            symptom_match = re.search(
                r'"symptom"\s*:\s*"([^"]*)"',
                cleaned,
                flags=re.DOTALL,
            )

            return {
                "symptom": (
                    symptom_match.group(1)
                    if symptom_match
                    else ""
                ),
                "assemblies_to_check": values,
            }

        raise ValueError(
            "Diagnostic Agent returned "
            "invalid JSON."
        )

    # ========================================================
    # GROUND ASSEMBLY NAMES
    # ========================================================

    def _ground_assemblies(
        self,
        assemblies,
        catalogue_text,
        current_assembly,
    ):

        catalogue_normalised = (
            self._normalise(
                catalogue_text
            )
        )

        current_normalised = (
            self._normalise(
                current_assembly
            )
        )

        grounded = []
        seen = set()

        for assembly in assemblies:

            if not isinstance(
                assembly,
                str,
            ):

                continue

            assembly = (
                assembly.strip()
            )

            normalised = (
                self._normalise(
                    assembly
                )
            )

            if not normalised:
                continue

            # Never recommend the assembly
            # currently being inspected.

            if (
                current_normalised
                and normalised
                == current_normalised
            ):

                continue

            # The assembly must exist in the
            # supplied first-20-page catalogue text.

            if (
                normalised
                not in catalogue_normalised
            ):

                continue

            if normalised in seen:
                continue

            grounded.append(
                assembly
            )

            seen.add(
                normalised
            )

            if len(
                grounded
            ) >= 5:

                break

        return grounded

    # ========================================================
    # MAIN INVOKE
    # ========================================================

    def invoke(
        self,
        symptom,
        catalogue_path,
        catalogue_name="",
        current_assembly="",
    ):

        symptom = str(
            symptom or ""
        ).strip()

        if not symptom:

            return {
                "status": "failed",
                "error": (
                    "Symptom cannot be empty."
                ),
                "symptom": "",
                "assemblies_to_check": [],
            }

        try:

            # ------------------------------------------------
            # IMPORTANT:
            #
            # ONLY FIRST 20 PAGES ARE READ.
            # ------------------------------------------------

            catalogue_text = (
                self._extract_catalogue_text(
                    catalogue_path
                )
            )

            if not catalogue_text.strip():

                raise ValueError(
                    "No readable text was found "
                    "in the first "
                    f"{self.MAX_INDEX_PAGES} "
                    "pages of the catalogue."
                )

            # ------------------------------------------------
            # Build prompt
            # ------------------------------------------------

            prompt = (
                DIAGNOSTIC_PROMPT.format(
                    catalogue_name=(
                        catalogue_name
                        or Path(
                            catalogue_path
                        ).stem
                    ),
                    current_assembly=(
                        current_assembly
                        or "None"
                    ),
                    catalogue_text=(
                        catalogue_text
                    ),
                    symptom=symptom,
                )
            )

            # ------------------------------------------------
            # LLM
            # ------------------------------------------------

            response = (
                self.llm.invoke(
                    prompt
                )
            )

            # ------------------------------------------------
            # Parse
            # ------------------------------------------------

            data = (
                self._parse_json(
                    response
                )
            )

            # ------------------------------------------------
            # Validate
            # ------------------------------------------------

            validated = (
                DiagnosticOutput.model_validate(
                    data
                )
            )

            # ------------------------------------------------
            # Ground
            # ------------------------------------------------

            grounded = (
                self._ground_assemblies(
                    validated.assemblies_to_check,
                    catalogue_text,
                    current_assembly,
                )
            )

            return {
                "status": "completed",
                "error": "",
                "symptom": symptom,
                "assemblies_to_check": grounded,
            }

        except Exception as exc:

            return {
                "status": "failed",
                "error": (
                    f"Diagnostic Agent error: "
                    f"{exc}"
                ),
                "symptom": symptom,
                "assemblies_to_check": [],
            }