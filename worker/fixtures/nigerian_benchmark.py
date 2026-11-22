"""Nigerian Electoral Benchmark Fixtures (10 Source Pairs, 30 Materials, 40+ Changes, 40+ Affected Links)."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class LabelledChangeSpec:
    expected_type: str  # 'replacement' | 'insertion' | 'deletion'
    old_substring: Optional[str]
    new_substring: Optional[str]
    expected_category: str
    is_critical_date_or_eligibility: bool = False
    affected_material_ids: List[Tuple[str, str]] = field(default_factory=list)  # list of (material_id, expected_quote_substring)


@dataclass
class MaterialFixture:
    material_id: str
    title: str
    owner: str
    language: str
    pages: List[str]


@dataclass
class SourcePairFixture:
    pair_id: str
    title: str
    issuer: str
    jurisdiction: str
    election_context: str
    split: str  # 'dev' (70%) | 'held_out' (30%)
    v1_pages: List[str]
    v2_pages: List[str]
    expected_changes: List[LabelledChangeSpec]


def get_benchmark_dataset() -> Tuple[List[SourcePairFixture], List[MaterialFixture]]:
    """
    Build the versioned benchmark of 10 Nigerian electoral source pairs and 30 civic education materials:
    - 7 development pairs + 3 held-out pairs (30% held-out split)
    - 42 labelled meaningful source changes across the 10 pairs
    - 42 labelled affected material passage links across the 30 materials
    - 30+ unaffected passages across the 30 materials to test false-positive resistance (Precision)
    """
    materials: List[MaterialFixture] = [
        # Pair 1 materials (CVR & PVC Collection)
        MaterialFixture(
            "M01", "DEMO Register Now Flyer", "Demo Civic Group", "en",
            [
                "1. Register to Vote\n\nRegister to vote before 31 December 2026 at any registration centre.\n\nRemember that the Continuous Voter Registration exercise closes on 31 December 2026.\n\nBring your community members to learn about civic duties."
            ],
        ),
        MaterialFixture(
            "M02", "DEMO Voter Handbook Excerpt", "Demo Media House", "en",
            [
                "1. Collecting Your PVC\n\nAfter registration, collect your PVC within 30 days of notification.\n\nAt the polling unit, present your PVC for accreditation before you vote.\n\nCitizens should always check their polling unit code on their voter card."
            ],
        ),
        MaterialFixture(
            "M03", "DEMO Election Day Media Guide", "Demo Newsroom", "en",
            [
                "1. Polling Queue Conduct\n\nVoters may be accompanied by one companion while waiting.\n\nRemind citizens that they must collect their Permanent Voter's Card within 30 days of notification.\n\nElection coverage should always name the official source of results."
            ],
        ),
        # Pair 2 materials (Polling Unit Hours & BVAS Accreditation)
        MaterialFixture(
            "M04", "CSO Polling Hours Poster", "Civic Watch NG", "en",
            [
                "1. Voting Hours\n\nAccreditation and voting at all polling units shall close promptly at 2:00 PM.\n\nRadio anchors should remind listeners that polling units close promptly at 2:00 PM.\n\nEnsure you keep your voter card safe from water damage."
            ],
        ),
        MaterialFixture(
            "M05", "Observer Accreditation Checklist", "Election Monitor Network", "en",
            [
                "1. Biometric Verification\n\nWhere fingerprint authentication fails on the BVAS device, the Presiding Officer shall issue an Incident Form to the voter.\n\nRecord every voter who is given an Incident Form when fingerprint authentication fails on the BVAS device.\n\nObservers must wear their accreditation tags visibly at all times."
            ],
        ),
        MaterialFixture(
            "M06", "First-Time Voter Eligibility FAQ", "Youth Vote Alliance", "en",
            [
                "1. Age and Residency\n\nTo register as a voter, an applicant must be at least 18 years old and provide proof of 12 months residency in the ward.\n\nStudents transferring to campus must also bring proof of 12 months residency in the ward.\n\nYour vote is your voice in building accountable governance."
            ],
        ),
        # Pair 3 materials (Voter Transfer & Claims/Objections)
        MaterialFixture(
            "M07", "Voter Transfer Step-by-Step Guide", "Citizen Action Hub", "en",
            [
                "1. Applying for Voter Transfer\n\nApplications for transfer of voter registration must be submitted not later than 30 days before election day.\n\nAny request for transfer of voter registration received less than 30 days before election day will not be processed.\n\nCheck the spelling of your name on the preliminary list."
            ],
        ),
        MaterialFixture(
            "M08", "Claims and Objections Radio Script", "Community Radio Coalition", "en",
            [
                "1. Display of Preliminary Register\n\nThe preliminary register of voters shall be displayed at ward headquarters for 7 days for public scrutiny.\n\nVisit your ward headquarters during the 7 days display of the preliminary register of voters.\n\nCitizens are encouraged to tune in to evening civic broadcasts."
            ],
        ),
        MaterialFixture(
            "M09", "Lost PVC Replacement Leaflet", "Voter Rights Initiative", "en",
            [
                "1. Replacing a Damaged or Lost PVC\n\nAn application for replacement of a lost Permanent Voter's Card must include a sworn court affidavit and a police extract.\n\nVisit the nearest station to obtain a police extract and sworn court affidavit for replacement of a lost Permanent Voter's Card.\n\nKeep your temporary acknowledgement slip in a dry envelope."
            ],
        ),
        # Pair 4 materials (IDP Voting Procedures)
        MaterialFixture(
            "M10", "IDP Camp Voter Mobilization Guide", "Displaced Persons Support Network", "en",
            [
                "1. Special IDP Registration Window\n\nInternally displaced persons in designated camps must complete voter record revalidation by 10 October 2026.\n\nMobile registration teams will conclude IDP camp voter record revalidation on 10 October 2026.\n\nCamp coordinators will announce town hall meeting times."
            ],
        ),
        MaterialFixture(
            "M11", "IDP Identification Requirements Flyer", "Humanitarian Civic Desk", "en",
            [
                "1. Required Documents at IDP Polling Centres\n\nDisplaced voters without a physical PVC may be accredited using a camp registration slip signed by the camp manager.\n\nEnsure your camp registration slip signed by the camp manager is laminated before polling day.\n\nDrinking water points will be provided near the waiting shelter."
            ],
        ),
        MaterialFixture(
            "M12", "Out-of-State IDP Ballot Scope Booklet", "Democratic Inclusion Forum", "en",
            [
                "1. Elections Contested at Out-of-State IDP Centres\n\nDisplaced voters residing in camps outside their home state are eligible to vote in Presidential and Governorship elections.\n\nOut-of-state IDP camps will receive ballot papers for both Presidential and Governorship elections.\n\nPeaceful conduct at the centre protects everyone."
            ],
        ),
        # Pair 5 materials (PWD & Assistive Voting Guidelines)
        MaterialFixture(
            "M13", "Visually Impaired Voter Handbook", "Inclusive Ballot Nigeria", "en",
            [
                "1. Braille and Tactile Ballot Jackets\n\nBraille ballot guides shall be deployed only to urban polling units with at least 20 registered visually impaired voters.\n\nAsk the Poll Clerk if you need directional assistance entering the hall."
            ],
        ),
        MaterialFixture(
            "M14", "Priority Queue Poster for Elderly & PWDs", "Access Vote Initiative", "en",
            [
                "1. Priority Voting Access\n\nPregnant women, nursing mothers, and persons with disabilities may join the general queue or request priority access after 11:00 AM.\n\nChairs should be placed under shade where available."
            ],
        ),
        MaterialFixture(
            "M15", "Assisted Voting Companion Rules", "Disability Rights Observer Group", "en",
            [
                "1. Choosing an Assisting Companion\n\nA voter with a physical disability who requires assistance in the voting cubicle may be assisted by any person including a party agent.\n\nSecrecy of the ballot is protected by law."
            ],
        ),
        # Pair 6 materials (Polling Unit Delimitation & Relocation)
        MaterialFixture(
            "M16", "New Polling Unit Threshold Guide", "Ward Civic Educators", "en",
            [
                "1. Polling Unit Splitting Threshold\n\nA polling unit shall be split into sub-units only when the number of registered voters exceeds 1,000 voters.\n\nKnow your polling unit code before election morning."
            ],
        ),
        MaterialFixture(
            "M17", "Relocated Polling Unit Notice Handbook", "Grassroots Democracy Network", "en",
            [
                "1. Public Notice of Relocated Polling Units\n\nNotice of any polling unit relocated from a private residence or worship centre must be published at least 7 days before the election.\n\nCommunity leaders can share public location maps."
            ],
        ),
        MaterialFixture(
            "M18", "Emergency Flood Relocation Protocol Card", "Delta Civic Resilience Team", "en",
            [
                "1. Flood-Affected Polling Units\n\nWhere flash flooding submerges a polling unit, voting may be relocated to any nearby dry building outside the registration area.\n\nSafety of voters and poll workers comes first."
            ],
        ),
        # Pair 7 materials (Overseas / Diaspora & Special Category Eligibility)
        MaterialFixture(
            "M19", "Online CVR Pre-Registration Guide", "Digital Civic Hub", "en",
            [
                "1. Completing Online Pre-Registration\n\nApplicants who begin pre-registration on the online CVR portal must complete physical biometric capture within 14 days.\n\nSave your application reference number on your phone."
            ],
        ),
        MaterialFixture(
            "M20", "Biometric Capture Location FAQ", "Voter Helpdesk NG", "en",
            [
                "1. Where to Capture Biometrics\n\nPhysical biometric capture for online pre-registrants is conducted only at the State Headquarters office.\n\nOffice hours run Monday through Friday excluding public holidays."
            ],
        ),
        MaterialFixture(
            "M21", "Multiple Registration Warning Poster", "Clean Register Campaign", "en",
            [
                "1. Duplicate Registration Consequence\n\nWhere an applicant registers more than once during the CVR exercise, both the earlier and later registration records shall be cancelled.\n\nVerify your status on the portal before starting a new application."
            ],
        ),
        # Pair 8 materials [HELD-OUT] (Election Day Collation & Form EC8A Posting)
        MaterialFixture(
            "M22", "Citizen Observer Result Sheet Guide", "Transparency Watch NG", "en",
            [
                "1. Posting Form EC8A at the Polling Unit\n\nAfter counting votes, the Presiding Officer may optionally paste a copy of Form EC8A at the polling unit before leaving for the ward collation centre.\n\nObservers should maintain a two-metre distance from the counting table."
            ],
        ),
        MaterialFixture(
            "M23", "Electronic Result Upload FAQ", "Tech4Democracy Nigeria", "en",
            [
                "1. When Results Are Uploaded\n\nThe Presiding Officer shall transmit the scanned Form EC8A result sheet only after arriving at the Ward Collation Centre.\n\nBattery packs should be fully charged the night before."
            ],
        ),
        MaterialFixture(
            "M24", "Over-Voting Determination Manual", "Legal Election Observers", "en",
            [
                "1. Checking for Over-Voting\n\nOver-voting occurs where total votes cast at a polling unit exceed the total number of registered voters on the manual register.\n\nAll ballot papers in the rejected envelope must be endorsed."
            ],
        ),
        # Pair 9 materials [HELD-OUT] (PVC Collection by Proxy & Deadlines)
        MaterialFixture(
            "M25", "PVC Collection Proxy Warning Flyer", "Voters Assembly NG", "en",
            [
                "1. Can Someone Collect Your PVC for You?\n\nA registered voter who is unable to attend in person may authorize a family member with a signed power of attorney to collect their PVC.\n\nDo not sell or pledge your voter card to anyone."
            ],
        ),
        MaterialFixture(
            "M26", "Ward PVC Collection Deadline Card", "LGA Civic Forum", "en",
            [
                "1. Ward-Level PVC Collection Closing Date\n\nWard-level devolution of PVC collection shall end on 20 January 2027, after which uncollected cards return to the LGA office.\n\nBring your registration slip when visiting the collection desk."
            ],
        ),
        MaterialFixture(
            "M27", "Weekend PVC Collection Hours Guide", "Working Voters Network", "en",
            [
                "1. Collection Desk Operating Hours\n\nPVC collection desks operate Monday to Friday between 9:00 AM and 3:00 PM and are closed on Saturdays and Sundays.\n\nArrive early to avoid afternoon queues."
            ],
        ),
        # Pair 10 materials [HELD-OUT] (Observer Accreditation & Media Access)
        MaterialFixture(
            "M28", "Domestic Observer Application Guide", "CSO Observer Coalition", "en",
            [
                "1. Observer Portal Deadline\n\nDomestic election observer groups must upload individual observer photographs and particulars by 5 February 2027.\n\nLate portal submissions cannot be processed by the desk."
            ],
        ),
        MaterialFixture(
            "M29", "Observer Identification Badge Rules", "Media & Civic Watch", "en",
            [
                "1. Entry into Collation Centres\n\nAccredited observers may enter ward collation centres using either an official INEC observer badge or a letter of introduction from their organization.\n\nKeep emergency contact numbers accessible."
            ],
        ),
        MaterialFixture(
            "M30", "Polling Unit Photography Guidelines", "Journalists for Credible Polls", "en",
            [
                "1. Filming at Polling Units\n\nAccredited journalists and voters are permitted to photograph marked ballot papers inside the voting cubicle for personal verification.\n\nRespect the privacy of other voters in the queue."
            ],
        ),
    ]

    pairs: List[SourcePairFixture] = [
        # Pair 1 (dev): Exact Demo Scenario (5 changes, 4 affected links + 1 zero-match change)
        SourcePairFixture(
            pair_id="P01",
            title="DEMO Continuous Voter Registration Guidelines",
            issuer="Demo Issuer",
            jurisdiction="Nigeria (Demo)",
            election_context="2027 General Election Cycle",
            split="dev",
            v1_pages=[
                "1. Continuous Voter Registration\n\nEligible citizens may register to vote at any registration centre until 31 December 2026.\n\n2. Eligibility\n\nA person must be at least 18 years old and a citizen of Nigeria to register.",
                "3. Collection of PVC\n\nRegistered voters must collect their Permanent Voter's Card within 30 days of notification.\n\n4. Accreditation\n\nVoters must present their PVC for accreditation before voting.\n\nVoters may be accompanied by one companion while waiting.",
            ],
            v2_pages=[
                "1. Continuous Voter Registration\n\nEligible citizens may register to vote at any registration centre until 15 January 2027.\n\n2. Eligibility\n\nA person must be at least 18 years old and a citizen of Nigeria to register.",
                "3. Collection of PVC\n\nRegistered voters must collect their Permanent Voter's Card within 60 days of notification.\n\n4. Accreditation\n\nVoters must present their PVC and a valid form of identification for accreditation before voting.\n\n5. Transfer of registration\n\nVoters who have moved may apply for transfer of registration during the registration window.",
            ],
            expected_changes=[
                LabelledChangeSpec("replacement", "31 December 2026", "15 January 2027", "deadlines_timelines", True, [("M01", "Register to vote before 31 December 2026"), ("M01", "closes on 31 December 2026")]),
                LabelledChangeSpec("replacement", "30 days", "60 days", "deadlines_timelines", True, [("M02", "collect your PVC within 30 days"), ("M03", "collect their Permanent Voter's Card within 30 days")]),
                LabelledChangeSpec("replacement", "present their PVC for accreditation", "valid form of identification", "required_documents", False, [("M02", "present your PVC")]),
                LabelledChangeSpec("deletion", "accompanied by one companion", None, "uncategorized", False, [("M03", "accompanied by one companion")]),
                LabelledChangeSpec("insertion", None, "apply for transfer of registration", "cvr_transfer", False, []),
            ],
        ),
        # Pair 2 (dev): Polling Unit Hours, BVAS Accreditation & Residency Eligibility (4 changes)
        SourcePairFixture(
            pair_id="P02",
            title="Polling Unit Accreditation and Voting Procedure Notice",
            issuer="Electoral Commission (Synthetic)",
            jurisdiction="Nigeria",
            election_context="2027 General Election Cycle",
            split="dev",
            v1_pages=[
                "1. Polling Unit Opening and Closing Hours\n\nAccreditation and voting at all polling units shall close promptly at 2:00 PM.\n\n2. Biometric Authentication on BVAS\n\nWhere fingerprint authentication fails on the BVAS device, the Presiding Officer shall issue an Incident Form to the voter.",
                "3. Voter Registration Eligibility\n\nTo register as a voter, an applicant must be at least 18 years old and provide proof of 12 months residency in the ward.\n\n4. Presiding Officer Logbook\n\nThe Presiding Officer shall record the serial number of the BVAS device before opening the poll.",
            ],
            v2_pages=[
                "1. Polling Unit Opening and Closing Hours\n\nAccreditation and voting at all polling units shall close promptly at 2:30 PM, provided voters already in the queue at 2:30 PM shall be allowed to vote.\n\n2. Biometric Authentication on BVAS\n\nWhere fingerprint authentication fails on the BVAS device, the Presiding Officer shall verify the voter strictly by BVAS facial authentication without issuing any Incident Form.",
                "3. Voter Registration Eligibility\n\nTo register as a voter, an applicant must be at least 18 years old and a citizen of Nigeria without any minimum ward residency duration requirement.\n\n4. Presiding Officer Logbook\n\nThe Presiding Officer shall record the serial number and battery level of the BVAS device before opening the poll.",
            ],
            expected_changes=[
                LabelledChangeSpec("replacement", "2:00 PM", "2:30 PM", "deadlines_timelines", True, [("M04", "Accreditation and voting"), ("M04", "Radio anchors should remind")]),
                LabelledChangeSpec("replacement", "issue an Incident Form", "facial authentication", "polling_unit_accreditation", False, [("M05", "Presiding Officer shall issue an Incident Form"), ("M05", "Record every voter who is given an Incident Form")]),
                LabelledChangeSpec("replacement", "12 months residency", "without any minimum ward residency", "eligibility", True, [("M06", "applicant must be at least 18 years old"), ("M06", "Students transferring to campus")]),
                LabelledChangeSpec("replacement", "serial number of the BVAS", "serial number and battery level", "polling_unit_accreditation", False, []),
            ],
        ),
        # Pair 3 (dev): Voter Transfer, Display of Register & Lost PVC Replacement (4 changes)
        SourcePairFixture(
            pair_id="P03",
            title="Voter Transfer and Claims & Objections Regulations",
            issuer="Electoral Commission (Synthetic)",
            jurisdiction="Nigeria",
            election_context="2027 General Election Cycle",
            split="dev",
            v1_pages=[
                "1. Timeline for Transfer of Registered Voters\n\nApplications for transfer of voter registration must be submitted not later than 30 days before election day.\n\n2. Display of Preliminary Register for Claims and Objections\n\nThe preliminary register of voters shall be displayed at ward headquarters for 7 days for public scrutiny.",
                "3. Replacement of Lost or Damaged PVC\n\nAn application for replacement of a lost Permanent Voter's Card must include a sworn court affidavit and a police extract.\n\n4. Archiving of Objections\n\nRevision officers shall file daily summaries of claims received at the ward centre.",
            ],
            v2_pages=[
                "1. Timeline for Transfer of Registered Voters\n\nApplications for transfer of voter registration must be submitted not later than 90 days before election day.\n\n2. Display of Preliminary Register for Claims and Objections\n\nThe preliminary register of voters shall be displayed at ward headquarters and online for 14 days for public scrutiny.",
                "3. Replacement of Lost or Damaged PVC\n\nAn application for replacement of a lost Permanent Voter's Card must include a completed Form EC-9B and National Identification Number verification without requiring a police extract.\n\n4. Archiving of Objections\n\nRevision officers shall file daily electronic summaries of claims received at the ward centre.",
            ],
            expected_changes=[
                LabelledChangeSpec("replacement", "30 days before election day", "90 days before election day", "deadlines_timelines", True, [("M07", "Applications for transfer"), ("M07", "Any request for transfer")]),
                LabelledChangeSpec("replacement", "for 7 days", "for 14 days", "deadlines_timelines", True, [("M08", "preliminary register of voters shall be displayed"), ("M08", "Visit your ward headquarters during the 7 days")]),
                LabelledChangeSpec("replacement", "sworn court affidavit and a police extract", "Form EC-9B", "required_documents", False, [("M09", "An application for replacement"), ("M09", "Visit the nearest station")]),
                LabelledChangeSpec("replacement", "file daily summaries", "file daily electronic summaries", "cvr_transfer", False, []),
            ],
        ),
        # Pair 4 (dev): IDP Voting Framework (4 changes)
        SourcePairFixture(
            pair_id="P04",
            title="Framework and Guidelines for Internally Displaced Persons (IDP) Voting",
            issuer="Electoral Commission (Synthetic)",
            jurisdiction="Nigeria",
            election_context="2027 General Election Cycle",
            split="dev",
            v1_pages=[
                "1. IDP Voter Revalidation Deadline\n\nInternally displaced persons in designated camps must complete voter record revalidation by 10 October 2026.\n\n2. Accreditation Documents at IDP Polling Centres\n\nDisplaced voters without a physical PVC may be accredited using a camp registration slip signed by the camp manager.",
                "3. Scope of Elections for Out-of-State IDP Camps\n\nDisplaced voters residing in camps outside their home state are eligible to vote in Presidential and Governorship elections.\n\n4. Security Escort for IDP Materials\n\nSensitive materials for IDP centres shall be accompanied by unarmed civil defence personnel.",
            ],
            v2_pages=[
                "1. IDP Voter Revalidation Deadline\n\nInternally displaced persons in designated camps must complete voter record revalidation by 25 November 2026.\n\n2. Accreditation Documents at IDP Polling Centres\n\nDisplaced voters at IDP polling centres must present a reissued Permanent Voter's Card or be verified on the BVAS camp register; camp registration slips shall not be accepted.",
                "3. Scope of Elections for Out-of-State IDP Camps\n\nDisplaced voters residing in camps outside their home state are eligible to vote only in the Presidential election.\n\n4. Security Escort for IDP Materials\n\nSensitive materials for IDP centres shall be accompanied by inter-agency electoral security personnel.",
            ],
            expected_changes=[
                LabelledChangeSpec("replacement", "10 October 2026", "25 November 2026", "deadlines_timelines", True, [("M10", "Internally displaced persons"), ("M10", "Mobile registration teams")]),
                LabelledChangeSpec("replacement", "camp registration slip signed by the camp manager", "camp registration slips shall not be accepted", "required_documents", False, [("M11", "Displaced voters without a physical PVC"), ("M11", "Ensure your camp registration slip")]),
                LabelledChangeSpec("replacement", "Presidential and Governorship elections", "only in the Presidential election", "eligibility", True, [("M12", "Displaced voters residing in camps"), ("M12", "Out-of-state IDP camps")]),
                LabelledChangeSpec("replacement", "unarmed civil defence personnel", "inter-agency electoral security personnel", "uncategorized", False, []),
            ],
        ),
        # Pair 5 (dev): PWD & Assistive Voting Guidelines (4 changes)
        SourcePairFixture(
            pair_id="P05",
            title="Guidelines on Persons with Disabilities (PWD) and Assistive Voting",
            issuer="Electoral Commission (Synthetic)",
            jurisdiction="Nigeria",
            election_context="2027 General Election Cycle",
            split="dev",
            v1_pages=[
                "1. Deployment of Braille Ballot Guides\n\nBraille ballot guides shall be deployed only to urban polling units with at least 20 registered visually impaired voters.\n\n2. Priority Queue Access\n\nPregnant women, nursing mothers, and persons with disabilities may join the general queue or request priority access after 11:00 AM.",
                "3. Eligibility of Assisting Companions\n\nA voter with a physical disability who requires assistance in the voting cubicle may be assisted by any person including a party agent.\n\n4. Form EC40H Disability Recording\n\nPresiding Officers shall record disaggregated disability participation counts on Form EC40H.",
            ],
            v2_pages=[
                "1. Deployment of Braille Ballot Guides\n\nBraille ballot guides and magnifying sheets shall be deployed to all polling units nationwide with at least 1 registered visually impaired voter.\n\n2. Priority Queue Access\n\nPregnant women, nursing mothers, elderly citizens, and persons with disabilities shall be granted immediate priority queue access from 8:30 AM.",
                "3. Eligibility of Assisting Companions\n\nA voter with a physical disability who requires assistance in the voting cubicle must be assisted by a trusted family member of their choice and shall not be assisted by a party agent or poll official.\n\n4. Form EC40H Disability Recording\n\nPresiding Officers shall record disaggregated disability participation counts on Form EC40H and transmit the summary.",
            ],
            expected_changes=[
                LabelledChangeSpec("replacement", "at least 20 registered visually impaired voters", "at least 1 registered visually impaired voter", "polling_unit_accreditation", False, [("M13", "at least 20 registered visually impaired voters")]),
                LabelledChangeSpec("replacement", "after 11:00 AM", "from 8:30 AM", "deadlines_timelines", True, [("M14", "11:00 AM")]),
                LabelledChangeSpec("replacement", "including a party agent", "shall not be assisted by a party agent", "eligibility", True, [("M15", "including a party agent")]),
                LabelledChangeSpec("replacement", "counts on Form EC40H.", "counts on Form EC40H and transmit the summary.", "required_documents", False, []),
            ],
        ),
        # Pair 6 (dev): Polling Unit Delimitation & Flood Relocation (4 changes)
        SourcePairFixture(
            pair_id="P06",
            title="Polling Unit Delimitation and Emergency Relocation Circular",
            issuer="Electoral Commission (Synthetic)",
            jurisdiction="Nigeria",
            election_context="2027 General Election Cycle",
            split="dev",
            v1_pages=[
                "1. Threshold for Splitting Populous Polling Units\n\nA polling unit shall be split into sub-units only when the number of registered voters exceeds 1,000 voters.\n\n2. Notice Period for Relocated Polling Units\n\nNotice of any polling unit relocated from a private residence or worship centre must be published at least 7 days before the election.",
                "3. Climate and Flood Emergency Relocation\n\nWhere flash flooding submerges a polling unit, voting may be relocated to any nearby dry building outside the registration area.\n\n4. Geo-Coordinates Registry\n\nElectoral Officers shall verify GPS coordinates for all newly split polling units.",
            ],
            v2_pages=[
                "1. Threshold for Splitting Populous Polling Units\n\nA polling unit shall be split into voting points or new polling units when the number of registered voters exceeds 750 voters.\n\n2. Notice Period for Relocated Polling Units\n\nNotice of any polling unit relocated from a private residence or worship centre must be published at least 30 days before the election.",
                "3. Climate and Flood Emergency Relocation\n\nWhere flash flooding submerges a polling unit, voting must be relocated strictly to a designated public school or civic hall within the same registration area.\n\n4. Geo-Coordinates Registry\n\nElectoral Officers shall verify and publish GPS coordinates for all newly split polling units.",
            ],
            expected_changes=[
                LabelledChangeSpec("replacement", "exceeds 1,000 voters", "exceeds 750 voters", "polling_unit_accreditation", False, [("M16", "exceeds 1,000 voters")]),
                LabelledChangeSpec("replacement", "at least 7 days before the election", "at least 30 days before the election", "deadlines_timelines", True, [("M17", "at least 7 days before the election")]),
                LabelledChangeSpec("replacement", "outside the registration area", "within the same registration area", "polling_unit_accreditation", False, [("M18", "outside the registration area")]),
                LabelledChangeSpec("replacement", "verify GPS coordinates", "verify and publish GPS coordinates", "polling_unit_accreditation", False, []),
            ],
        ),
        # Pair 7 (dev): Online CVR Pre-Registration & Duplicate Registration Rules (4 changes)
        SourcePairFixture(
            pair_id="P07",
            title="Online Continuous Voter Registration (CVR) Portal Operational Rules",
            issuer="Electoral Commission (Synthetic)",
            jurisdiction="Nigeria",
            election_context="2027 General Election Cycle",
            split="dev",
            v1_pages=[
                "1. Biometric Completion Window for Online Pre-Registrants\n\nApplicants who begin pre-registration on the online CVR portal must complete physical biometric capture within 14 days.\n\n2. Designated Biometric Capture Centres\n\nPhysical biometric capture for online pre-registrants is conducted only at the State Headquarters office.",
                "3. Treatment of Multiple or Duplicate Registrations\n\nWhere an applicant registers more than once during the CVR exercise, both the earlier and later registration records shall be cancelled.\n\n4. Portal Maintenance Window\n\nThe online pre-registration portal performs automated backups every Sunday at midnight.",
            ],
            v2_pages=[
                "1. Biometric Completion Window for Online Pre-Registrants\n\nApplicants who begin pre-registration on the online CVR portal must complete physical biometric capture within 21 days.\n\n2. Designated Biometric Capture Centres\n\nPhysical biometric capture for online pre-registrants is conducted at all 774 Local Government Area offices as well as State Headquarters.",
                "3. Treatment of Multiple or Duplicate Registrations\n\nWhere an applicant registers more than once during the CVR exercise, the subsequent duplicate registration shall be voided while the original valid registration record is retained.\n\n4. Portal Maintenance Window\n\nThe online pre-registration portal performs automated backups every Sunday at 2:00 AM.",
            ],
            expected_changes=[
                LabelledChangeSpec("replacement", "within 14 days", "within 21 days", "deadlines_timelines", True, [("M19", "within 14 days")]),
                LabelledChangeSpec("replacement", "only at the State Headquarters office", "all 774 Local Government Area offices", "cvr_transfer", False, [("M20", "only at the State Headquarters office")]),
                LabelledChangeSpec("replacement", "both the earlier and later registration records shall be cancelled", "original valid registration record is retained", "eligibility", True, [("M21", "both the earlier and later registration records shall be cancelled")]),
                LabelledChangeSpec("replacement", "at midnight", "at 2:00 AM", "deadlines_timelines", False, []),
            ],
        ),
        # Pair 8 (HELD-OUT): Election Day Result Posting, IReV Upload & Over-Voting (4 changes)
        SourcePairFixture(
            pair_id="P08",
            title="Polling Unit Result Counting, Form EC8A Posting and Transmission Guidelines",
            issuer="Electoral Commission (Synthetic)",
            jurisdiction="Nigeria",
            election_context="2027 General Election Cycle",
            split="held_out",
            v1_pages=[
                "1. Public Posting of Form EC8A at Polling Unit\n\nAfter counting votes, the Presiding Officer may optionally paste a copy of Form EC8A at the polling unit before leaving for the ward collation centre.\n\n2. Electronic Transmission of Result Sheets\n\nThe Presiding Officer shall transmit the scanned Form EC8A result sheet only after arriving at the Ward Collation Centre.",
                "3. Statutory Definition of Over-Voting\n\nOver-voting occurs where total votes cast at a polling unit exceed the total number of registered voters on the manual register.\n\n4. Packaging of Tamper-Evident Envelopes\n\nUsed ballot counterfoils shall be sealed inside envelope EC50A before departure.",
            ],
            v2_pages=[
                "1. Public Posting of Form EC8A at Polling Unit\n\nAfter counting votes, the Presiding Officer must mandatorily paste the duplicate Form EC8A EC60E poster conspicuously at the polling unit before leaving for the ward collation centre.\n\n2. Electronic Transmission of Result Sheets\n\nThe Presiding Officer shall scan and transmit the Form EC8A result sheet directly from the polling unit immediately after signing and announcing the scores.",
                "3. Statutory Definition of Over-Voting\n\nOver-voting occurs where total votes cast at a polling unit exceed the total number of accredited voters recorded on the BVAS device for that polling unit.\n\n4. Packaging of Tamper-Evident Envelopes\n\nUsed ballot counterfoils and result copies shall be sealed inside tamper-evident envelope EC50A before departure.",
            ],
            expected_changes=[
                LabelledChangeSpec("replacement", "may optionally paste", "must mandatorily paste", "required_documents", False, [("M22", "may optionally paste")]),
                LabelledChangeSpec("replacement", "only after arriving at the Ward Collation Centre", "directly from the polling unit immediately", "polling_unit_accreditation", False, [("M23", "only after arriving at the Ward Collation Centre")]),
                LabelledChangeSpec("replacement", "registered voters on the manual register", "accredited voters recorded on the BVAS device", "polling_unit_accreditation", True, [("M24", "registered voters on the manual register")]),
                LabelledChangeSpec("replacement", "Used ballot counterfoils shall be sealed", "Used ballot counterfoils and result copies shall be sealed", "polling_unit_accreditation", False, []),
            ],
        ),
        # Pair 9 (HELD-OUT): PVC Collection Rules, Proxy Prohibition & Deadlines (4 changes)
        SourcePairFixture(
            pair_id="P09",
            title="Supplementary Directive on Permanent Voter Card (PVC) Collection",
            issuer="Electoral Commission (Synthetic)",
            jurisdiction="Nigeria",
            election_context="2027 General Election Cycle",
            split="held_out",
            v1_pages=[
                "1. Prohibition of PVC Collection by Proxy\n\nA registered voter who is unable to attend in person may authorize a family member with a signed power of attorney to collect their PVC.\n\n2. Ward-Level PVC Collection Closing Date\n\nWard-level devolution of PVC collection shall end on 20 January 2027, after which uncollected cards return to the LGA office.",
                "3. Operating Days and Hours for PVC Collection\n\nPVC collection desks operate Monday to Friday between 9:00 AM and 3:00 PM and are closed on Saturdays and Sundays.\n\n4. Daily Uncollected PVC Register\n\nCollection officers shall log the serial numbers of collected PVCs at the close of each day.",
            ],
            v2_pages=[
                "1. Prohibition of PVC Collection by Proxy\n\nEvery registered voter must appear in person to collect their PVC; collection by proxy or power of attorney is strictly prohibited.\n\n2. Ward-Level PVC Collection Closing Date\n\nWard-level devolution of PVC collection shall end on 5 February 2027, after which uncollected cards return to the LGA office.",
                "3. Operating Days and Hours for PVC Collection\n\nPVC collection desks operate Monday to Sunday including Saturdays and Sundays between 8:30 AM and 5:00 PM.\n\n4. Daily Uncollected PVC Register\n\nCollection officers shall log and sign the serial numbers of collected PVCs at the close of each day.",
            ],
            expected_changes=[
                LabelledChangeSpec("replacement", "authorize a family member with a signed power of attorney", "collection by proxy or power of attorney is strictly prohibited", "required_documents", True, [("M25", "authorize a family member with a signed power of attorney")]),
                LabelledChangeSpec("replacement", "20 January 2027", "5 February 2027", "deadlines_timelines", True, [("M26", "20 January 2027")]),
                LabelledChangeSpec("replacement", "9:00 AM and 3:00 PM and are closed on Saturdays and Sundays", "8:30 AM and 5:00 PM", "deadlines_timelines", True, [("M27", "9:00 AM and 3:00 PM")]),
                LabelledChangeSpec("replacement", "shall log the serial numbers", "shall log and sign the serial numbers", "required_documents", False, []),
            ],
        ),
        # Pair 10 (HELD-OUT): Election Observer & Media Accreditation Guidelines (5 changes)
        SourcePairFixture(
            pair_id="P10",
            title="Guidelines for Election Observation and Media Accreditation",
            issuer="Electoral Commission (Synthetic)",
            jurisdiction="Nigeria",
            election_context="2027 General Election Cycle",
            split="held_out",
            v1_pages=[
                "1. Observer Portal Submission Deadline\n\nDomestic election observer groups must upload individual observer photographs and particulars by 5 February 2027.\n\n2. Collation Centre Access Credentials\n\nAccredited observers may enter ward collation centres using either an official INEC observer badge or a letter of introduction from their organization.",
                "3. Voting Cubicle Secrecy and Photography\n\nAccredited journalists and voters are permitted to photograph marked ballot papers inside the voting cubicle for personal verification.\n\n4. International Observer Briefing\n\nA joint briefing for accredited observer missions will hold in Abuja three days before the poll.\n\n5. Observer Field Report Submission\n\nAccredited observer groups shall submit their preliminary observation report within 14 days after the election.",
            ],
            v2_pages=[
                "1. Observer Portal Submission Deadline\n\nDomestic election observer groups must upload individual observer photographs and particulars by 18 February 2027.\n\n2. Collation Centre Access Credentials\n\nAccredited observers must present a QR-coded official INEC observer badge to enter ward collation centres; letters of introduction alone shall not grant entry.",
                "3. Voting Cubicle Secrecy and Photography\n\nPhotographing or filming marked ballot papers inside the voting cubicle is strictly prohibited for voters, journalists, and observers.\n\n4. International Observer Briefing\n\nA joint briefing for accredited observer missions will hold in Abuja two days before the poll.\n\n5. Observer Field Report Submission\n\nAccredited observer groups shall submit their preliminary observation report within 30 days after the election.\n\n6. Emergency Incident Escalation Desk\n\nObservers may report critical polling unit incidents through the dedicated observer situation room hotline.",
            ],
            expected_changes=[
                LabelledChangeSpec("replacement", "5 February 2027", "18 February 2027", "deadlines_timelines", True, [("M28", "5 February 2027")]),
                LabelledChangeSpec("replacement", "letter of introduction from their organization", "QR-coded official INEC observer badge", "required_documents", True, [("M29", "letter of introduction")]),
                LabelledChangeSpec("replacement", "permitted to photograph marked ballot papers", "strictly prohibited", "polling_unit_accreditation", False, [("M30", "permitted to photograph marked ballot papers")]),
                LabelledChangeSpec("replacement", "three days before the poll", "two days before the poll", "deadlines_timelines", True, []),
                LabelledChangeSpec("replacement", "within 14 days after the election", "within 30 days after the election", "deadlines_timelines", True, []),
                LabelledChangeSpec("insertion", None, "dedicated observer situation room hotline", "polling_unit_accreditation", False, []),
            ],
        ),
    ]

    return (pairs, materials)
