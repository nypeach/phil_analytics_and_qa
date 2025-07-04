# Immediate Post Payment Specification Preview

<details markdown="1">
<summary>Immediate Post Payments - "It Should" ✅</summary>

* `{payment.encs_to_check}` = `[]`
* `{payment.plas}` = `[]`
* `{payment.is_balanced}` should be `True`
* **IF** `{payment.is_balanced}` = `True` **AND** `{payment.is_split}` = `False`
   * It should Find the Batch
   * It should Update the Batch Totals
   * It should Post the Batch
   * It should update `{payment.posted}` = `"Y"`
   * It should update `{payment.note}` = `"Balanced-Batch Closed"`
   * It should Update the PMT Master
* **IF** `{payment.is_balanced}` = `True` **AND** `{payment.is_split}` = `True`
   * It should get all the `{payments}` **WHERE** `{payment.eft_num}` is the same
      * **IF** `{payments.is_balanced}` = `True` for **ALL** `{payments}`
         * It should Find the Batch
         * It should Update the Batch Totals
         * It should Post the Batch
         * It should update `{payment.posted}` = `"Y"`
         * It should update `{payment.note}` = `"Balanced-Batch Closed"`
         * It should Update the PMT Master
      * **IF** `{payments.is_balanced}` ≠ `True` for **ALL** `{payments}` **AND** `{payments.is_balanced}` = `True`
         * It should Find the Batch
         * It should Update the Batch Totals
         * It should Post the Batch
         * It should update `{payment.posted}` = `"Y"`
         * It should update `{payment.note}` = `"Balanced-Batch Not Closed"`
         * It should Update the PMT Master
* **IF** `{payment.is_balanced}` = `False`
   * It should update `{payment.posted}` = `"N"`
   * It should update `{payment.note}` = `"Not Balanced-Review"`
   * It should update `{run.status}` = `"Failed"`

</details>