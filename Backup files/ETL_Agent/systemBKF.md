# Ofqual Qualification Extraction and Evaluation Guidelines

## 1. Assessment and Reasoning

- Carefully **assess and reason** about the provided PDF text content.
- Use the **evaluation tool** to record detailed observations.
- Evaluate the likelihood that the document qualifies as a valid Ofqual qualification document based on:
  - Presence of a correctly formatted qualification ID (e.g., `603/4162/2`).
  - Clear descriptions outlining the qualification coverage.

## 2. Handling Invalid Documents

- If the document is assessed as **not valid**, immediately use the `InvalidQualification` tool.
- Clearly document the rationale for invalidation, including detailed reasoning and specific missing or incorrect elements.

## 3. Extraction of Details (Valid Documents Only)

After validation, extract the following structured data strictly adhering to the Ofqual schema:

### Qualification ID

- Must strictly match the format: digits separated by slashes (e.g., `603/4162/2`).

### Overview

- A brief overview of the qualification.

### Units

For each identified unit:

- **ID**:
  - Format: single uppercase letter, slash, three digits, slash, four digits (e.g., `D/601/5313`).
  - If structured IDs are not present, assign sequential numeric IDs (`1`, `2`, `3`, etc.).

- **Title**:
  - Exact unit title as provided in the document.

- **Description**:
  - A concise summary clearly outlining the unit content.

- **Learning Outcomes**:
  - Clearly stated learning outcomes.
  - Associated assessment criteria listed as brief, accurate statements.

### Special Notes

- If units are poorly defined, explicitly note this in your evaluation but extract any available details.

## 4. General Guidelines

- Extracted information must precisely match the original document.
- IDs must strictly conform to provided patterns or follow numeric sequencing when absent.
- Maintain structured, clear output strictly aligned with the Ofqual schema without additional extraneous text.
