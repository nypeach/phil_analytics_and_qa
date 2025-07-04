"""
PHIL Analytics and QA Library - QA It Shoulds

This module defines QA specifications for different payment types and scenarios.
Uses composable markdown strings to define expected behaviors for each payment type.
"""

# Reusable components for building payment scenarios
balancing = """* **IF** `{payment.is_balanced}` = `True` **AND** `{payment.is_split}` = `False`
    * It should Find the Batch
    * It should Update the Batch Totals
    * It should Post the Batch
    * It should update `{payment.posted}` = "Y"
    * It should update `{payment.note}` = "Balanced-Batch Closed"
    * It should Update the PMT Master
* **IF** `{payment.is_balanced}` = `True` **AND** `{payment.is_split}` = `True`
    * It should get all the `{payments}` **WHERE** `{payment.eft_num}` is the same
        * **IF** `{payments.is_balanced}` = `True` for **ALL** `{payments}`
            * It should Find the Batch
            * It should Update the Batch Totals
            * It should Post the Batch
            * It should update `{payment.posted}` = "Y"
            * It should update `{payment.note}` = "Balanced-Batch Closed"
            * It should Update the PMT Master
        * **IF** `{payments.is_balanced}` ≠ `True` for **ALL** `{payments}` **AND** `{payments.is_balanced}` = `True`
            * It should Find the Batch
            * It should Update the Batch Totals
            * It should Post the Batch
            * It should update `{payment.posted}` = "Y"
            * It should update `{payment.note}` = "Balanced-Batch Not Closed"
            * It should Update the PMT Master"""

not_balanced_handling = """* **IF** `{payment.is_balanced}` = `False`
    * It should update `{payment.posted}` = "N"
    * It should update `{payment.note}` = "Not Balanced-Review"
    * It should update `{run.status}` = "Failed\""""

# Payment type specifications using composable components
immediate_post_components = [
    """* `{payment.encs_to_check}` = `[]`
* `{payment.plas}` = `[]`
* `{payment.is_balanced}` should be `True`""",
    balancing,
    not_balanced_handling
]

pla_only_components = [
    """*Note: Payment will only be balanced if the Provider Level Adjustments are Interest, we don't do other PLAs*

* `{payment.encs_to_check}` = `[]`
* `{payment.plas}` ≠ `[]`
* `sum_of_plas` = the sum of `{code.amt}` for `{codes}` in `{payment.plas}`
* **IF** all `{code.code}` for `{code}` in `{pla.codes}` = "L6", for each code …
    * It should add a new encounter to NextGen
    * It should add the interest payment and interest adjustment to NextGen
    * It should change the status to "None" if the payer is not "Patient"
    * The payment **should be balanced** after adding the Interest
    * It should update the change log with "Added Interest"
    * `{payment.is_balanced}` should be `True`
* **IF** all `{code.code}` for `{code}` in `{pla.codes}` ≠ "L6"
    * `{payment.is_balanced}` should be `False`
    * There should be **ONLY** interest plas (L6)""",
    balancing,
    """* **IF** `{payment.is_balanced}` = `False`
    * **IF** the difference between `{payment.ledger_paid}` and `{payment.amt}` = `sum_of_plas`
        * It should update `{payment.note}` = "Not Balanced-PLAs"
        * It should update `{payment.posted}` = "N"
        * It should update `{run.status}` = "Success"
    * **IF** the difference between `{payment.ledger_paid}` and `{payment.amt}` ≠ `sum_of_plas`
        * It should update `{payment.note}` = "Not Balanced-Review"
        * It should update `{payment.posted}` = "N"
        * It should update `{run.status}` = "Failed"
        * It should Update the PMT Master"""
]

quick_post_components = [
    """* `{payment.encs_to_check}` ≠ `[]`
* `{payment.plas}` = `[]`
* It should **ONLY** have `{enc.type}` = "appeal_has_adj" **OR** "chg_equal_adj" **OR** "secondary_n408_pr96"
    * **IF** `{enc.type}` = "appeal_has_adj"
        * It should zero out the adjustment in NextGen
        * It should update the Change Log with `{service.cpt4}`, "Adjusted", `{service.adj_amt}`, "0.00", "Zeroed out Adjustment on Appeal"
    * **IF** `{enc.type}` = "chg_equal_adj"
        * **IF** `{payer}` = "WA ST L&I"
            * **IF** `{code.code}` = "CO119" it should **NOT** zero out the adjustment or update the change log
            * **IF** `{code.code}` ≠ "CO119" it should
                * It should zero out the adjustment on NextGen
                * It should update the Change Log with "Zeroed out Adjustment on Chg Equal Adj"
        * **IF** `{payer}` ≠ "WA ST L&I"
            * It should zero out the adjustment on NextGen
            * It should update the Change Log with "Zeroed out Adjustment on Chg Equal Adj"
    * **IF** `{enc.type}` = "secondary_n408_pr96"
        * It should have `{code.code}` = "N408" **AND** `{code.code}` = "PR96"
        * It should zero out the adjustment in NextGen
        * It should change the status to "Settled moved to self" in NextGen
        * It should add the "N408" to the reason codes in NextGen
        * It should update the Change Log with "Zeroed out Adjustment, Non-Covered Deductible, Settled to Self"
* `{payment.is_balanced}` should be `True`""",
    balancing,
    not_balanced_handling
]

full_post_components = [
    """* `{payment.encs_to_check}` ≠ `[]`
* `{payment.plas}` = `[]`
* There are **NO** "Not Posted" encounters
* It should **ONLY** have `{enc.type}` = "appeal_has_adj" **OR** "chg_equal_adj" **OR** "secondary_n408_pr96" **OR** "secondary_co94_oa94" **OR** "secondary_mc_tricare_dshs" **OR** "tertiary"
    * **IF** `{enc.type}` = "appeal_has_adj"
        * It should zero out the adjustment in NextGen
        * It should update the Change Log with "Zeroed out Adjustment on Appeal"
    * **IF** `{enc.type}` = "chg_equal_adj"
        * **IF** `{payer}` = "WA ST L&I"
            * **IF** `{code.code}` = "CO119" it should **NOT** zero out the adjustment or update the change log
            * **IF** `{code.code}` ≠ "CO119" it should
                * It should zero out the adjustment on NextGen
                * It should update the Change Log with "Zeroed out Adjustment on Chg Equal Adj"
        * **IF** `{payer}` ≠ "WA ST L&I"
            * It should zero out the adjustment on NextGen
            * It should update the Change Log with "Zeroed out Adjustment on Chg Equal Adj"
    * **IF** `{enc.type}` = "secondary_n408_pr96"
        * It should have `{code.code}` = "N408" **AND** `{code.code}` = "PR96"
        * It should zero out the adjustment in NextGen
        * It should change the status to "Settled moved to self" in NextGen
        * It should add the "N408" to the reason codes in NextGen
        * It should update the Change Log with "Zeroed out Adjustment, Non-Covered Deductible, Settled to Self"
    * **IF** `{enc.type}` = "secondary_co94_oa94"
        * It should update the adj field in next gen to `bal` + `adj`
        * It should update change log with "Adjusted off patient balance on Secondary with CO94"
    * **IF** `{enc.type}` = "secondary_mc_tricare_dshs"
        * It should update the adj field in next gen to (`bal` - `pr`) + `adj`
        * It should update change log with "Adjusted off patient balance on Secondary for `payer` payment"
    * **IF** `{enc.type}` = "tertiary"
        * It should update change log with "Adjusted off patient balance on Secondary for `payer` payment"
* `{payment.is_balanced}` should be `True`""",
    balancing,
    not_balanced_handling
]

mixed_post_components = [
    """* `{payment.encs_to_check}` ≠ `[]`
* It should have at least one "Not Posted" encounter

### Provider Level Adjustments

* **IF** `{payment.plas}` ≠ `[]`
    * **IF** `{code.code}` for `{code}` in `{pla.codes}` = "L6"
    * It should add a new encounter to NextGen
    * It should add the interest payment and interest adjustment to NextGen
    * It should change the status to "None" if the payer is not "Patient"
    * The payment **should be balanced** after adding the Interest
    * It should update the change log with "Added Interest"

### **Posted Encounters**

* **IF** `{enc.type}` = "appeal_has_adj"
    * It should zero out the adjustment in NextGen
    * It should update the Change Log with "Zeroed out Adjustment on Appeal"
* **IF** `{enc.type}` = "chg_equal_adj"
    * **IF** `{payer}` = "WA ST L&I"
        * **IF** `{code.code}` = "CO119" it should **NOT** zero out the adjustment or update the change log
        * **IF** `{code.code}` ≠ "CO119" it should
            * It should zero out the adjustment on NextGen
            * It should update the Change Log with "Zeroed out Adjustment on Chg Equal Adj"
    * **IF** `{payer}` ≠ "WA ST L&I"
        * It should zero out the adjustment on NextGen
        * It should update the Change Log with "Zeroed out Adjustment on Chg Equal Adj"
* **IF** `{enc.type}` = "secondary_n408_pr96"
    * It should have `{code.code}` = "N408" **AND** `{code.code}` = "PR96"
    * It should zero out the adjustment in NextGen
    * It should change the status to "Settled moved to self" in NextGen
    * It should add the "N408" to the reason codes in NextGen
    * It should update the Change Log with "Zeroed out Adjustment, Non-Covered Deductible, Settled to Self"
* **IF** `{enc.type}` = "secondary_co94_oa94"
    * It should update the adj field in next gen to `bal` + `adj`
    * It should update change log with "Adjusted off patient balance on Secondary with CO94"
* **IF** `{enc.type}` = "secondary_mc_tricare_dshs"
    * It should update the adj field in next gen to (`bal` - `pr`) + `adj`
    * It should update change log with "Adjusted off patient balance on Secondary for `payer` payment"
* **IF** `{enc.type}` = "tertiary"
    * It should update change log with "Adjusted off patient balance on Secondary for `payer` payment"

### **Not Posted Encounters**

* **IF** `{enc.type}` = "other_not_posted"
    * It should update the Change Log with the `service["desc"]` as the Note
    * ***NOTE: The entire payment will not be balanced***
* **IF** `{enc.type}` = "enc_payer_not_found" **OR** the entire encounter is "Not Posted"
    * **IF** there is a "Received Invalid Encounter Number Alert" **OR** "Received Pre-listed for Bad Debt Alert" message
        * It should update the Change Log with the message
    * It should match the Policy Nbr to find the Payer
    * **IF** it does **NOT** find the matching Payer
        * It should add "Patient" as the Payer
        * It should post the payments to the service lines
        * It should update the Change Log with "Added Unidentified Payer Encounter"
        * It should go to the next `{enc}` in `{payment.encs_to_check}`
    * **IF** it **DOES** finds the matching Payer it should
        * It should update the Change Log with "Added Found Payer Encounter"
        * For each `service["cpt4"]`, It should post the `service["cpt4"]` payment in NextGen
        * It should follow the rules below for **After Payment Has Been Posted**
* **IF** `{enc.type}` ="multiple_to_one" **OR** "svc_no_match_clm"
    * It should post the `service["cpt4"]` payment in NextGen
    * It should follow the rules below for **After Payment Has Been Posted**
* **IF** `{enc.type}` = "chg_mismatch_cpt4"
    * It should find the `cpt4` of the "Not Posted" in the service pair
    * It should find the `opposite_cpt4` in the service pair
    * If the `opposite_cpt4` is in NextGen
        * It should post the payment to the `opposite_cpt4` line
        * It should zero out the adjustment
        * It should set the status to "Appeal"
        * It should update the Change Log with "Posted `cpt4` on `opposite_cpt4` Line"
    * If the `cpt4` is in NextGen and the `opposite_cpt4` is not in NextGen
        * It should post the payment to the `cpt4` line
        * It should zero out the adjustment
        * It should set the status to "Appeal"
        * It should update the Change Log with "Posted `cpt4` on Voided Line"
    * If the `cpt4` and the `opposite_cpt4` are both not in NextGen
        * It should update the Change Log with "Charge Mismatch on CPT4 no Matching Visit Codes in NextGen"
        * It should mark it for TA/PS Review
    * It should go to the next `{enc}` in `{payment.encs_to_check}`

### **After Payment Has Been Posted**

**FOR** each "Not Posted" service line added **WHERE** Payer ≠ "Patient"

* **IF** the `service["clm_status"]` Begins with 22
    * **IF** there is another `encounter` with the same `encounter["num"]` and a different `encounter["clm_status"]`
        * JMS put what Process Reversals with Recoupment Function
    * **IF** there is **NOT** another `encounter` with the same `encounter["num"]` and a different `encounter["clm_status"]`
        * JMS put what the Process Reversal with No Recoupment Function does
* **IF** the `service["clm_status"]` Does **NOT** begin with 22
    * **IF** there is another `encounter` with the same `encounter["num"]` and a `encounter["clm_status"]` begins with "22"
    * JMS put what Process Reversals with Recoupment Function
* **IF** the `NG.Status` = "Appeal"
    * It should zero out the adjustment in NextGen
    * It should update the Change Log with `{service.cpt4}`, "Adjusted", `{service.adj_amt}`, "0.00", "Zeroed out Adjustment on Appeal"
* **IF** `NG.Qty/Charges` = `NG.Adj`
    * **IF** `{payer}` = "WA ST L&I"
        * **IF** `{code.code}` = "CO119" it should **NOT** zero out the adjustment or update the change log
        * **IF** `{code.code}` ≠ "CO119" it should
            * It should zero out the adjustment on NextGen
            * It should update the Change Log with `{service.cpt4}`, "Adjusted", `{service.adj_amt}`, "0.00", "Zeroed out Adjustment on Chg Equal Adj"
    * **IF** `{payer}` ≠ "WA ST L&I"
        * It should zero out the adjustment on NextGen
        * It should update the Change Log with `{service.cpt4}`, "Adjusted", `{service.adj_amt}`, "0.00", "Zeroed out Adjustment on Chg Equal Adj"
* **IF** `{service.clm_status}` does not begin with "22" and does begin with "2" or "20" **AND** `{code.code}` = "N408" **AND** `{code.code}` = "PR96" **AND** (CO45 **OR** OA23)
    * It should have `{code.code}` = "N408" **AND** `{code.code}` = "PR96"
    * It should zero out the adjustment in NextGen
    * It should change the status to "Settled moved to self" in NextGen
    * It should add the "N408" to the reason codes in NextGen
    * It should update the Change Log with `{service.cpt4}`, "Adjusted", `{service.adj_amt}`, "0.00", "Zeroed out Adjustment, Non-Covered Deductible, Settled to Self"
* **IF** `{service.clm_status}` does not begin with "22" and does begin with "2" or "20" **AND** `{code.code}` = "CO94" **OR** "OA94"
    * It should update the adj field in next gen to `bal` + `adj`
    * It should update `{payment.note}` = "Adjusted off patient balance on Secondary with CO94"
* **IF** `{service.clm_status}` does not begin with "22" and does begin with "2" or "20" **AND** `{run.payer}` = "Medicare" **OR** "Tricare" **OR** "DSHS"
    * It should update the adj field in next gen to (`bal` - `pr`) + `adj`
    * It should update `{payment.note}` = "Adjusted off patient balance on Secondary for `payer` payment"
* **IF** `{service.clm_status}` begins with "3"
    * It should update `{payment.note}` = "Adjusted off patient balance on Secondary for `payer` payment"
    * `changes` should be updated to {"cpt4": `fn_service["cpt4"]`, "changed": "Status", "from": `status`, "to": "Appeal", "note": `note`}

### Balancing

* **IF** there is **ANY** `{enc.type}` = "other_not_posted" **IN** `{encs_to_check}` **THEN** `{payment.is_balanced}` should be `False`
    * **IF** the difference between `{payment.ledger_paid}` and `{payment.amt}` = `sum_other_not_posted` + `sum_of_plas` ✅
    * **IF** the difference between `{payment.ledger_paid}` and `{payment.amt}` ≠ `sum_other_not_posted` + `sum_of_plas` ❌
    * **IF** `{payment.is_balanced}` = `False`
        * It should update `{payment.posted}` = "N"
        * It should update `{payment.note}` = "Not Balanced-Review"
        * It should update `{run.status}` = "Failed"
* **IF** there is **NO** `{enc.type}` = "other_not_posted" **IN** `{encs_to_check}`
    * **IF** `{payment.plas}` = `[]` **THEN** `{payment.is_balanced}` should be `True`
        * **IF** `{payment.is_balanced}` = `False`
            * It should update `{payment.posted}` = "N"
            * It should update `{payment.note}` = "Not Balanced-Review"
            * It should update `{run.status}` = "Failed"
    * **IF** `{payment.plas}` ≠ `[]` **AND** `{payment.plas}` is **ONLY** interest **THEN** `{payment.is_balanced}` should be `True`
    * **IF** `{payment.plas}` ≠ `[]` **AND** `{payment.plas}` is **NOT** only interest **THEN** `{payments.is_balanced}` = `False`
        * **IF** the difference between `{payment.ledger_paid}` and `{payment.amt}` = `sum_of_plas`
            * It should update `{payment.note}` = "Not Balanced-PLAs"
            * It should update `{payment.posted}` = "N"
            * It should update `{run.status}` = "Success"
        * **IF** the difference between `{payment.ledger_paid}` and `{payment.amt}` ≠ `sum_of_plas`
            * It should update `{payment.note}` = "Not Balanced-Review"
            * It should update `{payment.posted}` = "N"
            * It should update `{run.status}` = "Failed"
            * It should Update the PMT Master""",
    """* **IF** `{payment.is_balanced}` = `True` **AND** `{payment.is_split}` = `False`
    * It should Find the Batch
    * It should Update the Batch Totals
    * It should Post the Batch
    * It should update `{payment.posted}` = "Y"
    * It should update `{payment.note}` = "Balanced-Batch Closed"
    * It should Update the PMT Master
* **IF** `{payment.is_balanced}` = `True` **AND** `{payment.is_split}` = `True`
    * It should get all the `{payments}` **WHERE** `{payment.eft_num}` is the same
        * **IF** `{payments.is_balanced}` = `True` for **ALL** `{payments}`
            * It should Find the Batch
            * It should Update the Batch Totals
            * It should Post the Batch
            * It should update `{payment.posted}` = "Y"
            * It should update `{payment.note}` = "Balanced-Batch Closed"
            * It should Update the PMT Master
        * **IF** `{payments.is_balanced}` ≠ `True` for **ALL** `{payments}` **AND** `{payments.is_balanced}` = `True`
            * It should Find the Batch
            * It should Update the Batch Totals
            * It should Post the Batch
            * It should update `{payment.posted}` = "Y"
            * It should update `{payment.note}` = "Balanced-Batch Not Closed"
            * It should Update the PMT Master"""
]

# Helper function to combine components into final specifications
def combine_components(components):
    """
    Combine a list of markdown string components into a single specification.

    Args:
        components (list): List of markdown strings to combine

    Returns:
        str: Combined markdown specification
    """
    return '\n'.join(components)

# Final payment type specifications
immediate_post = combine_components(immediate_post_components)

pla_only = combine_components(pla_only_components)

quick_post = combine_components(quick_post_components)

full_post = combine_components(full_post_components)

mixed_post = combine_components(mixed_post_components)

# Dictionary mapping payment types to their specifications
PAYMENT_TYPE_SPECS = {
    "Immediate Post": immediate_post,
    "PLA Only": pla_only,
    "Quick Post": quick_post,
    "Full Post": full_post,
    "Mixed Post": mixed_post
}

# Toggle sections for markdown output
PAYMENT_TYPE_TOGGLES = {
    "Immediate Post": f"""<details markdown="1">
<summary>Immediate Post Payments - "It Should" ✅</summary>

{immediate_post}

</details>""",

    "PLA Only": f"""<details markdown="1">
<summary>PLA Only Payments - "It Should" ✅</summary>

{pla_only}

</details>""",

    "Quick Post": f"""<details markdown="1">
<summary>Quick Post Payments - "It Should" ✅</summary>

{quick_post}

</details>""",

    "Full Post": f"""<details markdown="1">
<summary>Full Post Payments - "It Should" ✅</summary>

{full_post}

</details>""",

    "Mixed Post": f"""<details markdown="1">
<summary>Mixed Post Payments - "It Should" ✅</summary>

{mixed_post}

</details>"""
}

# Encounter type categories (from PaymentTagger)
NOT_POSTED_LIST = [
    "enc_payer_not_found",
    "multiple_to_one",
    "other_not_posted",
    "svc_no_match_clm",
    "chg_mismatch_cpt4"
]

CHECK_NG_AND_DATA = [
    "secondary_co94_oa94",
    "secondary_mc_tricare_dshs",
    "tertiary"
]

REVERSALS = [
    "22_no_123",
    "22_with_123"
]

# Additional scenario specifications
eft_scenarios = {
    "split_eft": """
## Split EFT Scenarios

* **IF** `{eft.is_split}` = `True`
    * It should process each `{payment}` individually according to their payment type
    * It should only close the batch when **ALL** `{payments}` are balanced
    * It should track the EFT as "partially processed" until all payments are complete
    """,

    "not_split_eft": """
## Not Split EFT Scenarios

* **IF** `{eft.is_split}` = `False`
    * It should process the single `{payment}` according to its payment type
    * It should close the batch immediately if the payment is balanced
    """
}

# Special handling scenarios
special_scenarios = {
    "pla_handling": """
## PLA Handling Scenarios

* **IF** `{payment.plas.pla_l6}` ≠ `[]`
    * It should apply L6 adjustments to the appropriate encounters
    * It should update encounter balances
    * It should track L6 adjustments in the audit log

* **IF** `{payment.plas.pla_other}` ≠ `[]`
    * It should apply other PLAs to the payment level
    * It should update payment balances
    * It should track other PLAs in the audit log
    """,

    "encounter_review": """
## Encounter Review Scenarios

* **IF** `{encounter.tags}` contains items from `not_posted_list`
    * It should mark the encounter as "requires correction"
    * It should prevent automatic posting
    * It should generate review items for manual handling

* **IF** `{encounter.tags}` contains items from `check_ng_and_data` or `reversals`
    * It should mark the encounter as "requires review"
    * It should allow conditional posting after review
    * It should generate review items for verification
    """
}

# Function "It Shoulds" definitions
FUNCTION_IT_SHOULDS = {
    "Handle Interest Payment Function": [
        "It should parse the PLA text to extract encounter details (enc_num, enc_status, enc_pol_nbr, amt)",
        "It should add a new encounter to NextGen",
        "It should match the policy number to determine the payer",
        "It should select 'Interest Payment' or 'Interest Payment - Unidentified' based on payer type",
        "It should select 'Interest Adjustment' or 'Interest Adj' based on payer type",
        "It should enter 'TBOT: Entered Interest Payment' in transaction notes",
        "It should enter the negative amount in both Pay and Adj fields",
        "It should recalculate and save the encounter"
    ],

    "Update Encounter Changes Function": [
        "It should update the Change Log with the specified note"
    ]
}

def get_payment_spec(payment_type):
    """
    Get the QA specification for a specific payment type.

    Args:
        payment_type (str): The payment type ("Immediate Post", "PLA Only", etc.)

    Returns:
        str: The QA specification markdown for that payment type
    """
    return PAYMENT_TYPE_SPECS.get(payment_type, "Unknown payment type")

def get_payment_toggle(payment_type):
    """
    Get the QA specification wrapped in a toggle for a specific payment type.

    Args:
        payment_type (str): The payment type ("Immediate Post", "PLA Only", etc.)

    Returns:
        str: The QA specification wrapped in a markdown toggle
    """
    return PAYMENT_TYPE_TOGGLES.get(payment_type, "Unknown payment type")

def get_function_it_shoulds(function_name):
    """
    Get the "It Should" statements for a specific function.

    Args:
        function_name (str): The function name (e.g., "Handle Interest Payment Function")

    Returns:
        list: List of "It should" statements for the function
    """
    return FUNCTION_IT_SHOULDS.get(function_name, [])

def get_all_specs():
    """
    Get all QA specifications as a formatted markdown document.

    Returns:
        str: Complete QA specifications document
    """
    markdown_content = []

    markdown_content.append("# PHIL Analytics QA Specifications\n")
    markdown_content.append("This document defines the expected behaviors for different payment types and scenarios.\n\n")

    # Add payment type specifications with toggles
    markdown_content.append("## Payment Type Specifications\n\n")

    for payment_type in ["Immediate Post", "PLA Only", "Quick Post", "Full Post", "Mixed Post"]:
        markdown_content.append(f"{get_payment_toggle(payment_type)}\n\n")

    # Add EFT scenarios
    markdown_content.append("## EFT Scenarios\n")
    for scenario_name, spec in eft_scenarios.items():
        markdown_content.append(f"{spec}\n\n")

    # Add special scenarios
    markdown_content.append("## Special Handling Scenarios\n")
    for scenario_name, spec in special_scenarios.items():
        markdown_content.append(f"{spec}\n\n")

    # Add function "It Shoulds"
    markdown_content.append("## Function 'It Shoulds'\n\n")
    for function_name, it_shoulds in FUNCTION_IT_SHOULDS.items():
        markdown_content.append(f"### {function_name}\n")
        for it_should in it_shoulds:
            markdown_content.append(f"* {it_should}\n")
        markdown_content.append("\n")

    # Add encounter type references
    markdown_content.append("## Encounter Type Categories\n")
    markdown_content.append("### Not Posted List\n")
    for item in NOT_POSTED_LIST:
        markdown_content.append(f"* {item}\n")

    markdown_content.append("\n### Check NG and Data\n")
    for item in CHECK_NG_AND_DATA:
        markdown_content.append(f"* {item}\n")

    markdown_content.append("\n### Reversals\n")
    for item in REVERSALS:
        markdown_content.append(f"* {item}\n")

    return ''.join(markdown_content)

def validate_payment_against_spec(payment_data, payment_type):
    """
    Validate a payment object against its QA specification.

    Args:
        payment_data (dict): Payment data object
        payment_type (str): Expected payment type

    Returns:
        dict: Validation results with pass/fail status and details
    """
    validation_results = {
        "payment_type": payment_type,
        "passed": False,
        "issues": [],
        "checks_performed": []
    }

    # Basic validation logic (can be expanded)
    encs_to_check = payment_data.get("encs_to_check", {})
    plas = payment_data.get("plas", {"pla_l6": [], "pla_other": []})

    validation_results["checks_performed"].append(f"Checking payment type: {payment_type}")

    if payment_type == "Immediate Post":
        if len(encs_to_check) == 0 and len(plas["pla_l6"]) == 0 and len(plas["pla_other"]) == 0:
            validation_results["passed"] = True
        else:
            validation_results["issues"].append("Immediate Post should have no encounters to check and no PLAs")

    elif payment_type == "PLA Only":
        if len(encs_to_check) == 0 and (len(plas["pla_l6"]) > 0 or len(plas["pla_other"]) > 0):
            validation_results["passed"] = True
        else:
            validation_results["issues"].append("PLA Only should have no encounters to check but should have PLAs")

    # Add more validation logic for other payment types as needed

    return validation_results

# Example usage and testing
if __name__ == "__main__":
    print("PHIL Analytics QA Specifications")
    print("=" * 50)

    # Test the component combination
    print("\nImmediate Post Specification:")
    print("-" * 30)
    print(immediate_post)

    print("\nPLA Only Specification:")
    print("-" * 30)
    print(pla_only)

    print("\nImmediate Post Toggle:")
    print("-" * 30)
    print(get_payment_toggle("Immediate Post"))

    print("\nPLA Only Toggle:")
    print("-" * 30)
    print(get_payment_toggle("PLA Only"))

    # Test getting function it shoulds
    print("\nHandle Interest Payment Function 'It Shoulds':")
    print("-" * 30)
    for it_should in get_function_it_shoulds("Handle Interest Payment Function"):
        print(f"* {it_should}")

    # Test getting specs
    print(f"\nAvailable payment types: {list(PAYMENT_TYPE_SPECS.keys())}")

    # Test validation (with dummy data)
    dummy_payment = {
        "encs_to_check": {},
        "plas": {"pla_l6": [], "pla_other": []}
    }

    validation = validate_payment_against_spec(dummy_payment, "Immediate Post")
    print(f"\nValidation result: {validation}")