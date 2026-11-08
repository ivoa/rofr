"""Matrix of OAI explorer-style HTTP probes (golden sample-derived)."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["OAIExplorerCase", "OAI_PHASE1_CASES"]

OAI_NS = "http://www.openarchives.org/OAI/2.0/"


@dataclass(frozen=True)
class OAIExplorerCase:
    """expect_error_one_of=None means OAI error must NOT be returned.

    Otherwise the response must contain oai:error with @code matching one entry,
    or only codes listed in ignore_errors (e.g. badArgument when badResumptionToken
    is the preferred code).

    optional_error_one_of allows success with no error, or an error whose @code is
    one of the listed values (ignore_errors still applies when an error is present).
    """

    name: str
    query_options: str
    role: str
    expect_error_one_of: frozenset[str] | None = None
    ignore_errors: frozenset[str] = frozenset()
    optional_error_one_of: frozenset[str] = frozenset()


OAI_PHASE1_CASES: list[OAIExplorerCase] = [
    OAIExplorerCase("Identify", "?verb=Identify", "oai", None),
    OAIExplorerCase("Identify (illegal_parameter)", "?verb=Identify&test=test", "oai", frozenset({"badArgument"})),
    OAIExplorerCase("ListMetadataFormats", "?verb=ListMetadataFormats", "oai", None),
    OAIExplorerCase("ListSets", "?verb=ListSets", "oai", None),
    OAIExplorerCase("ListIdentifiers (oai_dc)", "?verb=ListIdentifiers&metadataPrefix=oai_dc", "oai", None),
    OAIExplorerCase(
        "ListIdentifiers (oai_dc, ivo_managed)",
        "?verb=ListIdentifiers&metadataPrefix=oai_dc&set=ivo_managed",
        "oai",
        None,
    ),
    OAIExplorerCase(
        "ListIdentifiers (oai_dc, from/until)",
        "?verb=ListIdentifiers&metadataPrefix=oai_dc&from=2000-01-01&until=2000-01-01",
        "oai",
        optional_error_one_of=frozenset({"noRecordsMatch", "badArgument"}),
    ),
    OAIExplorerCase(
        "ListIdentifiers (oai_dc, illegal_set, illegal_from/until)",
        "?verb=ListIdentifiers&metadataPrefix=oai_dc&set=really_wrong_set&from=some_random_date&until=some_random_date",
        "oai",
        frozenset({"badArgument", "noSetHierarchy"}),
    ),
    OAIExplorerCase(
        "ListIdentifiers (oai_dc, from granularity != until granularity)",
        "?verb=ListIdentifiers&metadataPrefix=oai_dc&from=2001-01-01&until=2002-01-01T00:00:00Z",
        "oai",
        frozenset({"noRecordsMatch", "badArgument"}),
    ),
    OAIExplorerCase(
        "ListIdentifiers (oai_dc, from > until)",
        "?verb=ListIdentifiers&metadataPrefix=oai_dc&from=2000-01-01&until=1999-01-01",
        "oai",
        frozenset({"noRecordsMatch", "badArgument"}),
    ),
    OAIExplorerCase("ListIdentifiers ()", "?verb=ListIdentifiers", "oai", frozenset({"badArgument"})),
    OAIExplorerCase(
        "ListIdentifiers (illegal_mdp)",
        "?verb=ListIdentifiers&metadataPrefix=illegal_mdp",
        "oai",
        frozenset({"cannotDisseminateFormat", "badArgument"}),
    ),
    OAIExplorerCase(
        "ListIdentifiers (mdp, mdp)",
        "?verb=ListIdentifiers&metadataPrefix=oai_dc&metadataPrefix=oai_dc",
        "oai",
        frozenset({"badArgument"}),
    ),
    OAIExplorerCase(
        "ListIdentifiers (illegal_resumptiontoken)",
        "?verb=ListIdentifiers&resumptionToken=junktoken",
        "oai",
        frozenset({"badResumptionToken"}),
        frozenset({"badArgument"}),
    ),
    OAIExplorerCase(
        "ListIdentifiers (oai_dc, from YYYY-MM-DD)",
        "?verb=ListIdentifiers&metadataPrefix=oai_dc&from=2001-01-01",
        "oai",
        None,
    ),
    OAIExplorerCase(
        "ListIdentifiers (oai_dc, from YYYY-MM-DDThh:mm:ssZ)",
        "?verb=ListIdentifiers&metadataPrefix=oai_dc&from=2001-01-01T00:00:00Z",
        "oai",
        optional_error_one_of=frozenset({"badArgument"}),
    ),
    OAIExplorerCase(
        "ListIdentifiers (oai_dc, from YYYY)",
        "?verb=ListIdentifiers&metadataPrefix=oai_dc&from=2001",
        "oai",
        frozenset({"badArgument"}),
    ),
    OAIExplorerCase(
        "ListMetadataFormats (illegal_id)",
        "?verb=ListMetadataFormats&identifier=really_wrong_id",
        "oai",
        frozenset({"idDoesNotExist", "badArgument"}),
    ),
    OAIExplorerCase(
        "GetRecord (oai_dc)",
        "?verb=GetRecord&metadataPrefix=oai_dc",
        "oai",
        frozenset({"badArgument"}),
    ),
    OAIExplorerCase(
        "GetRecord (illegal_id, oai_dc)",
        "?verb=GetRecord&identifier=really_wrong_id&metadataPrefix=oai_dc",
        "oai",
        frozenset({"idDoesNotExist", "badArgument"}),
    ),
    OAIExplorerCase(
        "GetRecord (invalid_id, oai_dc)",
        "?verb=GetRecord&identifier=invalid%5C%22id&metadataPrefix=oai_dc",
        "oai",
        frozenset({"badArgument", "idDoesNotExist"}),
    ),
    OAIExplorerCase(
        "ListRecords (oai_dc, from/until)",
        "?verb=ListRecords&metadataPrefix=oai_dc&from=2000-01-01&until=2000-01-01",
        "oai",
        optional_error_one_of=frozenset({"noRecordsMatch", "badArgument"}),
    ),
    OAIExplorerCase(
        "ListRecords (oai_dc, illegal_set, illegal_from/until)",
        "?verb=ListRecords&metadataPrefix=oai_dc&set=really_wrong_set&from=some_random_date&until=some_random_date",
        "oai",
        frozenset({"badArgument", "noSetHierarchy"}),
    ),
    OAIExplorerCase("ListRecords", "?verb=ListRecords", "oai", frozenset({"badArgument"})),
    OAIExplorerCase(
        "ListRecords (oai_dc, from granularity != until granularity)",
        "?verb=ListRecords&metadataPrefix=oai_dc&from=2001-01-01&until=2002-01-01T00:00:00Z",
        "oai",
        frozenset({"noRecordsMatch", "badArgument"}),
    ),
    OAIExplorerCase(
        "ListRecords (oai_dc, until before earliestDatestamp)",
        "?verb=ListRecords&metadataPrefix=oai_dc&until=1969-01-01T00:00:00Z",
        "oai",
        frozenset({"noRecordsMatch", "badArgument"}),
    ),
    OAIExplorerCase(
        "ListRecords (oai_dc)",
        "?verb=ListRecords&metadataPrefix=oai_dc",
        "oai",
        None,
    ),
    OAIExplorerCase(
        "ListRecords (illegal_resumptiontoken)",
        "?verb=ListRecords&resumptionToken=junktoken",
        "oai",
        frozenset({"badResumptionToken"}),
        frozenset({"badArgument"}),
    ),
    OAIExplorerCase(
        "IllegalVerb",
        "?verb=IllegalVerb",
        "oai",
        frozenset({"badVerb"}),
    ),
]
