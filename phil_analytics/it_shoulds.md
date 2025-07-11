## Balancing

### Balanced Handling
* **IF** `{payment.is_balanced}` = `True` **AND** `{payment.is_split}` = `False`
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

### Not Balancing Handling

* **IF** `{payment.is_balanced}` = `False` **AND** `{payment.plas}` ≠ `[]`
    * **IF** the difference between `{payment.ledger_paid}` and `{payment.amt}` = `sum_of_plas`
        * It should update `{payment.note}` = "Not Balanced-PLAs"
        * It should update `{payment.posted}` = "N"
        * It should update `{run.status}` = "Success"
    * **IF** the difference between `{payment.ledger_paid}` and `{payment.amt}` ≠ `sum_of_plas`
        * It should update `{payment.note}` = "Not Balanced-Review"
        * It should update `{payment.posted}` = "N"
        * It should update `{run.status}` = "Failed"
        * It should Update the PMT Master
* **ELSE** `{payment.is_balanced}` = `False`  **AND** `{payment.plas}` = `[]`
    * It should update `{payment.posted}` = "N"
    * It should update `{payment.note}` = "Not Balanced-Review"
    * It should update `{run.status}` = "Failed

## Provider Level Adjustments

* **IF** `{payment.plas}` ≠ `[]`
    * **IF** `{code.code}` for `{code}` in `{pla.codes}` = "L6"
    * It should add a new encounter to NextGen
    * It should add the interest payment and interest adjustment to NextGen
    * It should change the status to "None" if the payer is not "Patient"
    * The payment **should be balanced** after adding the Interest
    * It should update the change log with "Added Interest"


## Immediate Post Payments

* `{payment.encs_to_check}` = `[]`
* `{payment.plas}` = `[]`
* `{payment.is_balanced}` should be `True`
* There are **NO** "Not Posted" encounters
* It Should Follow Balancing [Balancing](#balancing)


## PLA Only Payments
_Note: Payment will only be balanced if the Provider Level Adjustments are Interest, we don't do other PLAs_

* `{payment.encs_to_check}` = `[]`
* `{payment.plas}` ≠ `[]`
* There are **NO** "Not Posted" encounters
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
    * There should be **ONLY** interest plas (L6)
* It should follow balancing [Balancing](#balancing)


## Quick Post Payments

* `{payment.encs_to_check}` ≠ `[]`
* There are **NO** "Not Posted" encounters
* **IF** `{payment.plas}` ≠ `[]`
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
        * There should be **ONLY** interest plas (L6)
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
* **IF** `{payment.plas}` = `[]` **THEN** `{payment.is_balanced}` should be `True`
* It should follow balancing [Balancing](#balancing)

## Full Post Payments

* `{payment.encs_to_check}` ≠ `[]`
* **IF** `{payment.plas}` ≠ `[]`
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
        * There should be **ONLY** interest plas (L6)
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
* **IF** `{payment.plas}` = `[]` **THEN** `{payment.is_balanced}` should be `True`
* It should follow balancing [Balancing](#balancing)

## Mixed Post Payments

* `{payment.encs_to_check}` ≠ `[]`
* It should have at least one "Not Posted" encounter
* **IF** `{payment.plas}` ≠ `[]`
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
        * There should be **ONLY** interest plas (L6)

### Posted Encounters

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

### Not Posted Encounters

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

### After Payment Has Been Posted

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
* **IF** there is **ANY** `{enc.type}` = "other_not_posted" **IN** `{encs_to_check}` **THEN** `{payment.is_balanced}` should be `False`
    * **IF** the difference between `{payment.ledger_paid}` and `{payment.amt}` = `sum_other_not_posted` + `sum_of_plas` ✅
    * **IF** the difference between `{payment.ledger_paid}` and `{payment.amt}` ≠ `sum_other_not_posted` + `sum_of_plas` ❌
* **IF** there is **NO** `{enc.type}` = "other_not_posted" **IN** `{encs_to_check}`
    * **IF** `{payment.plas}` = `[]` **THEN** `{payment.is_balanced}` should be `True`
* It should follow balancing [Balancing](#balancing)
