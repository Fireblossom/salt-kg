"""
Knowledge Graph Loader for SALT-KG

Parses the salt-kg.json file and extracts field descriptions,
business rules, and semantic metadata that will guide code generation.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class FieldMetadata:
    """Metadata for a single field/column"""
    uri: str
    field_name: str
    field_description: str
    field_type: str
    field_details: str
    data_element_description: str
    is_target: bool = False
    refers_to: Optional[str] = None

    def get_business_rules(self) -> str:
        """Extract business rules from the data element description"""
        desc = self.data_element_description
        rules = []

        # Parse sections like ### Definition, ### Use, ### Procedure
        sections = ['Definition', 'Use', 'Procedure', 'Dependencies', 'Example']
        for section in sections:
            marker = f'### {section}'
            if marker in desc:
                start = desc.find(marker) + len(marker)
                # Find next section or end
                end = len(desc)
                for next_section in sections:
                    next_marker = f'### {next_section}'
                    if next_marker in desc[start:]:
                        potential_end = desc.find(next_marker, start)
                        if potential_end < end and potential_end > start:
                            end = potential_end
                rules.append(f"{section}: {desc[start:end].strip()}")

        return '\n'.join(rules) if rules else desc

    def to_prompt_context(self) -> str:
        """Convert to a format suitable for LLM prompt"""
        ctx = f"Field: {self.field_name}\n"
        ctx += f"Description: {self.field_description}\n"
        ctx += f"Type: {self.field_type}\n"
        if self.data_element_description:
            ctx += f"Business Rules:\n{self.get_business_rules()}\n"
        if self.refers_to:
            ctx += f"References: {self.refers_to}\n"
        return ctx


@dataclass
class ViewMetadata:
    """Metadata for a database view/table"""
    uri: str
    name: str
    description: str
    short_description: str
    details: str
    fields: Dict[str, FieldMetadata] = field(default_factory=dict)

    def get_target_fields(self) -> List[FieldMetadata]:
        """Get fields marked as prediction targets"""
        return [f for f in self.fields.values() if f.is_target]

    def get_field_by_name(self, name: str) -> Optional[FieldMetadata]:
        """Get field metadata by name (case-insensitive)"""
        name_upper = name.upper()
        return self.fields.get(name_upper)

    def to_prompt_context(self) -> str:
        """Convert to a format suitable for LLM prompt"""
        ctx = f"View: {self.name}\n"
        ctx += f"Description: {self.description}\n"
        if self.short_description:
            ctx += f"Purpose: {self.short_description}\n"
        return ctx


class KGLoader:
    """
    Loads and provides access to SALT-KG metadata.

    The Knowledge Graph contains semantic information about SAP sales data,
    including field descriptions, business rules, and relationships.
    """

    def __init__(self, kg_path: Optional[str] = None):
        """
        Initialize the KG loader.

        Args:
            kg_path: Path to salt-kg.json. If None, uses default location.
        """
        if kg_path is None:
            # Default path relative to this file
            kg_path = Path(__file__).parent.parent / 'data' / 'salt-kg' / 'salt-kg.json'

        self.kg_path = Path(kg_path)
        self.views: Dict[str, ViewMetadata] = {}
        self._raw_data: Dict = {}

        self._load()

    def _load(self):
        """Load and parse the knowledge graph JSON"""
        with open(self.kg_path, 'r', encoding='utf-8') as f:
            self._raw_data = json.load(f)

        # Parse each view
        for view_key, view_data in self._raw_data.items():
            view = ViewMetadata(
                uri=view_data.get('uri', ''),
                name=view_data.get('name', view_key),
                description=view_data.get('description', ''),
                short_description=view_data.get('shortDescription', ''),
                details=view_data.get('details', '')
            )

            # Parse fields
            for field_data in view_data.get('fields', []):
                field_name = field_data.get('fieldName', '').upper()
                target_col = field_data.get('target_column', '')

                field_meta = FieldMetadata(
                    uri=field_data.get('uri', ''),
                    field_name=field_name,
                    field_description=field_data.get('fieldDescription', ''),
                    field_type=field_data.get('fieldType', ''),
                    field_details=field_data.get('fieldDetails', ''),
                    data_element_description=field_data.get('dataElementDescription', ''),
                    is_target=bool(target_col),
                    refers_to=field_data.get('refers_to_field')
                )
                view.fields[field_name] = field_meta

            self.views[view_key] = view

    def get_view(self, view_name: str) -> Optional[ViewMetadata]:
        """Get metadata for a specific view"""
        return self.views.get(view_name)

    def get_field(self, field_name: str, view_name: Optional[str] = None) -> Optional[FieldMetadata]:
        """
        Get field metadata by name.

        Args:
            field_name: The field name to look up
            view_name: Optional view to search in. If None, searches all views.
        """
        field_name_upper = field_name.upper()

        if view_name:
            view = self.views.get(view_name)
            if view:
                return view.get_field_by_name(field_name_upper)
        else:
            # Search all views
            for view in self.views.values():
                field = view.get_field_by_name(field_name_upper)
                if field:
                    return field
        return None

    def get_all_target_fields(self) -> List[FieldMetadata]:
        """Get all fields marked as prediction targets across all views"""
        targets = []
        for view in self.views.values():
            targets.extend(view.get_target_fields())
        return targets

    def get_context_for_field(self, target_field: str,
                               related_fields: Optional[List[str]] = None) -> str:
        """
        Build a comprehensive context string for a target field.

        This context will be passed to the LLM to help it understand
        the business logic for generating prediction code.

        Args:
            target_field: The field we want to predict
            related_fields: Optional list of fields that may influence the target
        """
        context_parts = []

        # Get target field info
        target_meta = self.get_field(target_field)
        if target_meta:
            context_parts.append("=== TARGET FIELD ===")
            context_parts.append(target_meta.to_prompt_context())

        # Get related field info
        if related_fields:
            context_parts.append("\n=== RELATED FIELDS ===")
            for field_name in related_fields:
                field_meta = self.get_field(field_name)
                if field_meta:
                    context_parts.append(field_meta.to_prompt_context())
                    context_parts.append("---")

        return '\n'.join(context_parts)

    def get_schema_summary(self) -> str:
        """Get a summary of the entire schema for overview"""
        summary = []
        for view_name, view in self.views.items():
            summary.append(f"\n## {view_name}")
            summary.append(view.description)
            summary.append(f"Fields: {len(view.fields)}")

            # List target fields
            targets = view.get_target_fields()
            if targets:
                summary.append(f"Target Fields: {[t.field_name for t in targets]}")

        return '\n'.join(summary)
