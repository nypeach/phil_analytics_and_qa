"""
PHIL Analytics and QA Library - Markdown Generator

This module generates markdown files from the complete data object.
Creates {filename}_efts.md with encounters that need review.
Creates {filename}_it_shoulds.md with QA specifications for payment types.
"""

from typing import Dict, List, Optional
from pathlib import Path
from collections import defaultdict


class MarkdownGenerator:
    """
    Generates markdown files from the complete data object.
    Creates nested markdown with GitHub-style toggles for encounters that need review.
    Also creates QA specification markdown files with payment type "It Shoulds".
    """

    def __init__(self, payer_name: str):
        """
        Initialize the markdown generator.

        Args:
            payer_name (str): Name of the payer folder being processed
        """
        self.payer_name = payer_name

    def generate_efts_markdown(self, data_object: Dict, output_dir: str = ".", missing_encounter_efts: Optional[List[str]] = None, analytics_results: Optional[Dict] = None) -> str:
        """
        Generate {payer}_efts.md file with encounters that need review.

        Args:
            data_object (Dict): Complete data object with all EFTs, payments, encounters
            output_dir (str): Directory to save the markdown file
            missing_encounter_efts (List[str], optional): List of EFT NUMs with missing encounters
            analytics_results (Dict, optional): Analytics results from AnalyticsProcessor

        Returns:
            str: Path to the saved markdown file
        """
        print(f"📝 Generating EFTs markdown for {self.payer_name}...")

        markdown_content = []
        markdown_content.append(f"# {self.payer_name} EFTs Analysis\n\n")

        # Add missing encounter EFTs section at the top if any exist
        if missing_encounter_efts and len(missing_encounter_efts) > 0:
            self._generate_missing_encounter_efts_section(missing_encounter_efts, markdown_content)

        # Add Mixed Post Scenarios section
        if analytics_results:
            self._generate_mixed_post_scenarios_section(analytics_results, markdown_content)

        # Separate EFTs by split status
        not_split_efts = {}
        split_efts = {}

        for eft_num, eft in data_object.items():
            if eft['is_split']:
                split_efts[eft_num] = eft
            else:
                not_split_efts[eft_num] = eft

        # Generate "EFTs - Not Split" section grouped by payment status
        self._generate_not_split_section(not_split_efts, markdown_content)

        # Generate "EFTs - Split" section grouped by EFT
        self._generate_split_section(split_efts, markdown_content)

        # Save markdown file
        output_path = Path(output_dir) / f"{self.payer_name}_efts.md"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(markdown_content))

        print(f"   ✅ EFTs markdown saved to: {output_path}")
        return str(output_path)

    def generate_it_shoulds_markdown(self, output_dir: str = ".") -> str:
        """
        Generate {payer}_it_shoulds.md file with QA specifications for payment types only.

        Args:
            output_dir (str): Directory to save the markdown file

        Returns:
            str: Path to the saved markdown file
        """
        print(f"📝 Generating QA It Shoulds markdown for {self.payer_name}...")

        # Import the QA specifications
        try:
            from .qa_it_shoulds import PAYMENT_TYPE_TOGGLES
        except ImportError:
            print("   ⚠️ Warning: Could not import qa_it_shoulds module")
            return ""

        markdown_content = []
        markdown_content.append(f"# {self.payer_name} QA Specifications - \"It Shoulds\"\n\n")
        markdown_content.append("This document defines the expected behaviors for different payment types.\n\n")

        # Add payment type specifications with toggles - ONLY the payment types
        markdown_content.append("## Payment Type Specifications\n\n")

        # Define the order of payment statuses to match the standard order
        payment_types = ["Immediate Post", "PLA Only", "Quick Post", "Full Post", "Mixed Post"]

        for payment_type in payment_types:
            if payment_type in PAYMENT_TYPE_TOGGLES:
                markdown_content.append(f"{PAYMENT_TYPE_TOGGLES[payment_type]}\n\n")

        # Save markdown file
        output_path = Path(output_dir) / f"{self.payer_name}_it_shoulds.md"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(markdown_content))

        print(f"   ✅ QA It Shoulds markdown saved to: {output_path}")
        return str(output_path)

    def _generate_missing_encounter_efts_section(self, missing_encounter_efts: List[str], markdown_content: List[str]) -> None:
        """
        Generate the "EFTs with Encounters Not Found" section at the top of the markdown.

        Args:
            missing_encounter_efts (List[str]): List of EFT NUMs with missing encounters
            markdown_content (List[str]): List to append markdown content to
        """
        markdown_content.append(f"### EFTs with Encounters Not Found ({len(missing_encounter_efts)})\n\n")

        if missing_encounter_efts:
            for eft_num in sorted(missing_encounter_efts):
                markdown_content.append(f"* {eft_num}\n")
        else:
            markdown_content.append("None\n")

        markdown_content.append("\n")

    def _generate_mixed_post_scenarios_section(self, analytics_results: Dict, markdown_content: List[str]) -> None:
        """
        Generate the "Mixed Post Scenarios" section with analytics insights as H3 with nested toggles.

        Args:
            analytics_results (Dict): Analytics results from AnalyticsProcessor
            markdown_content (List[str]): List to append markdown content to
        """
        summary = analytics_results.get("summary", {})

        # Calculate total scenarios
        total_scenarios = (
            summary.get("mixed_post_no_plas_count", 0) +
            summary.get("mixed_post_l6_only_count", 0) +
            summary.get("charge_mismatch_cpt4_count", 0)
        )

        # Main Mixed Post Scenarios as H3
        markdown_content.append(f"### Mixed Post Scenarios ({total_scenarios})\n\n")

        # Mixed Post with No PLAs
        no_plas_count = summary.get("mixed_post_no_plas_count", 0)
        markdown_content.append(f"<details markdown=\"1\">\n<summary>Mixed Post with No PLAs ({no_plas_count})</summary>\n\n")

        if analytics_results.get("mixed_post_no_plas"):
            # Show ALL payments with most encounters to check first
            all_no_plas = analytics_results["mixed_post_no_plas"]  # Already sorted by encounters to check (descending)
            for payment in all_no_plas:
                markdown_content.append(f"* **{payment['practice_id']}_{payment['payment_num']}**: {payment['encs_to_check_count']} to Check\n")
        else:
            markdown_content.append("None found.\n")

        markdown_content.append("\n</details>\n\n")

        # Mixed Post with L6 PLAs Only
        l6_only_count = summary.get("mixed_post_l6_only_count", 0)
        markdown_content.append(f"<details markdown=\"1\">\n<summary>Mixed Post with L6 PLAs Only ({l6_only_count})</summary>\n\n")

        if analytics_results.get("mixed_post_l6_only"):
            # Show ALL payments with most encounters to check first
            all_l6_only = analytics_results["mixed_post_l6_only"]  # Already sorted by encounters to check (descending)
            for payment in all_l6_only:
                markdown_content.append(f"* **{payment['practice_id']}_{payment['payment_num']}**: {payment['encs_to_check_count']} to check, {payment['pla_l6_count']} L6 PLAs\n")
        else:
            markdown_content.append("None found.\n")

        markdown_content.append("\n</details>\n\n")

        # Charge Mismatch CPT4 Encounters
        charge_mismatch_count = summary.get("charge_mismatch_cpt4_count", 0)
        markdown_content.append(f"<details markdown=\"1\">\n<summary>Charge Mismatch CPT4 Encounters ({charge_mismatch_count})</summary>\n\n")

        if analytics_results.get("charge_mismatch_cpt4_encounters"):
            # Show ALL encounters with smallest number of encounters to check first (easier to review first)
            all_charge_mismatch = analytics_results["charge_mismatch_cpt4_encounters"]  # Already sorted by encounters to check (ascending)
            for encounter in all_charge_mismatch:
                markdown_content.append(f"* **{encounter['practice_id']}_{encounter['payment_num']}**: {encounter['encs_to_check_count']} to check\n")
        else:
            markdown_content.append("None found.\n")

        markdown_content.append("\n</details>\n\n")

        # Max Encounters to Check as H3 (separate from Mixed Post Scenarios)
        max_analysis = analytics_results.get("max_encounters_analysis", {})
        if max_analysis.get("not_split_single_payment") or max_analysis.get("split_single_eft"):
            markdown_content.append(f"### Max Encounters to Check\n\n")

            if max_analysis.get("not_split_single_payment"):
                max_payment = max_analysis["not_split_single_payment"]
                markdown_content.append(f"* **Not Split Payment:** {max_payment['practice_id']}_{max_payment['payment_num']} - {max_payment['encs_to_check_count']}\n")

            if max_analysis.get("split_single_eft"):
                max_eft = max_analysis["split_single_eft"]
                markdown_content.append(f"* **Split EFT:** {max_eft['eft_num']} - {max_eft['total_encs_to_check']}\n")

            markdown_content.append("\n")

    def _generate_not_split_section(self, not_split_efts: Dict, markdown_content: List[str]) -> None:
        """
        Generate the "EFTs - Not Split" section organized by payment status.

        Args:
            not_split_efts (Dict): Dictionary of not-split EFTs
            markdown_content (List[str]): List to append markdown content to
        """
        # Group payments by status
        payment_groups = defaultdict(list)

        for eft_num, eft in not_split_efts.items():
            # Each not-split EFT should have exactly one payment
            for payment_key, payment in eft["payments"].items():
                payment_status = payment.get("status", "Unknown")

                # Calculate counts
                encs_to_check_count = len(payment.get("encs_to_check", {}))
                total_encounters = len(payment.get("encounters", {}))
                pla_count = len(payment["plas"]["pla_l6"]) + len(payment["plas"]["pla_other"])

                payment_info = {
                    'payment_key': payment_key,
                    'eft_num': eft_num,
                    'practice_id': payment['practice_id'],
                    'pmt_num': payment['num'],
                    'encs_to_check_count': encs_to_check_count,
                    'total_encounters': total_encounters,
                    'pla_count': pla_count,
                    'payment': payment,
                    'eft': eft
                }

                payment_groups[payment_status].append(payment_info)

        # Define the order of payment statuses
        status_order = ["Immediate Post", "PLA Only", "Quick Post", "Full Post", "Mixed Post"]

        not_split_title = f"EFTs - Not Split ({len(not_split_efts)})"
        markdown_content.append(f"<details markdown=\"1\">\n<summary>{not_split_title}</summary>\n\n")

        for status in status_order:
            payments = payment_groups.get(status, [])
            status_title = f"{status} ({len(payments)})"
            markdown_content.append(f"<details markdown=\"1\">\n<summary>{status_title}</summary>\n\n")

            if payments:
                # Sort payments by practice_id then pmt_num
                sorted_payments = sorted(payments, key=lambda x: (x['practice_id'], x['pmt_num']))

                for payment_info in sorted_payments:
                    # Create payment title with updated format for not split
                    payment_title = f"{payment_info['practice_id']}_{payment_info['pmt_num']} (EFT: {payment_info['eft_num']}, Encs To Check: {payment_info['encs_to_check_count']}/{payment_info['total_encounters']}, PLAs: {payment_info['pla_count']})"

                    # Check if there's any content to show
                    has_plas = payment_info['pla_count'] > 0
                    has_encounters_to_check = payment_info['encs_to_check_count'] > 0
                    payment_status = payment_info['payment'].get('status', 'Unknown')

                    # Show collapsible section only if there are PLAs or encounters to check, and it's not Immediate Post
                    if (has_plas or has_encounters_to_check) and payment_status != "Immediate Post":
                        markdown_content.append(f"<details markdown=\"1\">\n<summary>{payment_title}</summary>\n\n")

                        # Add PLA amount breakdown if payment has PLAs
                        if has_plas:
                            self._generate_pla_amount_breakdown(payment_info['payment'], markdown_content)
                            markdown_content.append("\n")

                        # Add detailed payment content only if there are PLAs or encounters to check
                        self._generate_payment_details(payment_info['payment'], payment_info['eft'], markdown_content, has_plas, has_encounters_to_check)

                        markdown_content.append("</details>\n\n")
                    else:
                        # Just show the title without a collapsible section for Immediate Post or payments with no content
                        markdown_content.append(f"* {payment_title}\n\n")
            else:
                markdown_content.append("No payments in this category.\n\n")

            markdown_content.append("</details>\n\n")  # Close status group

        markdown_content.append("</details>\n\n")  # Close EFTs - Not Split

    def _generate_split_section(self, split_efts: Dict, markdown_content: List[str]) -> None:
        """
        Generate the "EFTs - Split" section organized by EFT number.

        Args:
            split_efts (Dict): Dictionary of split EFTs
            markdown_content (List[str]): List to append markdown content to
        """
        split_title = f"EFTs - Split ({len(split_efts)})"
        markdown_content.append(f"<details markdown=\"1\">\n<summary>{split_title}</summary>\n\n")

        for eft_num in sorted(split_efts.keys()):
            eft = split_efts[eft_num]

            # Calculate totals across all payments in this EFT
            total_encs_to_check = 0
            total_plas = 0

            for payment in eft["payments"].values():
                total_encs_to_check += len(payment.get("encs_to_check", {}))
                total_plas += len(payment["plas"]["pla_l6"]) + len(payment["plas"]["pla_other"])

            eft_title = f"{eft_num} (Payments: {len(eft['payments'])}, Encs To Check: {total_encs_to_check}, PLAs: {total_plas})"
            markdown_content.append(f"<details markdown=\"1\">\n<summary>{eft_title}</summary>\n\n")

            # Sort payments by practice_id then payment number
            sorted_payments = sorted(eft["payments"].items(),
                                   key=lambda x: (x[1]['practice_id'], x[1]['num']))

            for payment_key, payment in sorted_payments:
                # Calculate counts for this payment
                encs_to_check_count = len(payment.get("encs_to_check", {}))
                total_encounters = len(payment.get("encounters", {}))
                pla_count = len(payment["plas"]["pla_l6"]) + len(payment["plas"]["pla_other"])
                payment_status = payment.get("status", "Unknown")

                # Create payment title with updated format for split
                payment_title = f"{payment['practice_id']}_{payment['num']} (Status: {payment_status}, Encs To Check: {encs_to_check_count}/{total_encounters}, PLAs: {pla_count})"

                # Check if there's any content to show
                has_plas = pla_count > 0
                has_encounters_to_check = encs_to_check_count > 0

                # Show collapsible section only if there are PLAs or encounters to check, and it's not Immediate Post
                if (has_plas or has_encounters_to_check) and payment_status != "Immediate Post":
                    markdown_content.append(f"<details markdown=\"1\">\n<summary>{payment_title}</summary>\n\n")

                    # Add PLA amount breakdown if payment has PLAs
                    if has_plas:
                        self._generate_pla_amount_breakdown(payment, markdown_content)
                        markdown_content.append("\n")

                    # Add detailed payment content only if there are PLAs or encounters to check
                    self._generate_payment_details(payment, eft, markdown_content, has_plas, has_encounters_to_check)

                    markdown_content.append("</details>\n\n")  # Close payment
                else:
                    # Just show the title without a collapsible section for Immediate Post or payments with no content
                    markdown_content.append(f"* {payment_title}\n\n")

            markdown_content.append("</details>\n\n")  # Close EFT

        markdown_content.append("</details>\n\n")  # Close EFTs - Split

    def _generate_pla_amount_breakdown(self, payment: Dict, markdown_content: List[str]) -> None:
        """
        Generate the PLA amount breakdown for payments that have PLAs.
        Simple 3-line format: Payment Amount, Other PLAs, Ledger Balance.

        Args:
            payment (Dict): Payment object with PLA amounts
            markdown_content (List[str]): List to append markdown content to
        """
        # Get the amounts from the payment object
        payment_amount = payment.get("amt", 0.0)  # Payment Amount from the file split
        pla_other_amts = payment.get("pla_other_amts", 0.0)  # Total Other PLAs (can be positive or negative)

        # Calculate Ledger Balance: Payment Amount + Other PLAs
        # (Adding because PLAs are already in their correct sign - positive PLAs increase balance, negative PLAs decrease balance)
        ledger_balance = payment_amount + pla_other_amts

        # Simple 3-line format
        markdown_content.append(f"* Payment Amount: ${payment_amount:,.2f}\n")
        markdown_content.append(f"* Other PLAs: ${pla_other_amts:,.2f}\n")
        markdown_content.append(f"* Ledger Balance: ${ledger_balance:,.2f}\n")

    def _generate_payment_details(self, payment: Dict, eft: Dict, markdown_content: List[str], has_plas: bool = True, has_encounters_to_check: bool = True) -> None:
        """
        Generate the detailed content for a payment (PLAs and Encounters).
        Only generates sections that have content.

        Args:
            payment (Dict): Payment object
            eft (Dict): EFT object (for context)
            markdown_content (List[str]): List to append markdown content to
            has_plas (bool): Whether this payment has PLAs
            has_encounters_to_check (bool): Whether this payment has encounters to check
        """
        # PLA section - only show if there are PLAs
        if has_plas:
            pla_l6_count = len(payment["plas"]["pla_l6"])
            pla_other_count = len(payment["plas"]["pla_other"])
            pla_title = f"PLAs (L6: {pla_l6_count}, Other: {pla_other_count})"
            markdown_content.append(f"<details markdown=\"1\">\n<summary>{pla_title}</summary>\n\n")

            if payment["plas"]["pla_l6"]:
                markdown_content.append("**L6 PLAs:**\n")
                for pla in payment["plas"]["pla_l6"]:
                    markdown_content.append(f"- {pla}\n")
                markdown_content.append("\n")

            if payment["plas"]["pla_other"]:
                markdown_content.append("**Other PLAs:**\n")
                for pla in payment["plas"]["pla_other"]:
                    markdown_content.append(f"- {pla}\n")
                markdown_content.append("\n")

            markdown_content.append("</details>\n\n")

        # Encounters section - only show if there are encounters that need review
        if has_encounters_to_check:
            encs_to_check = payment.get("encs_to_check", {})
            encounters_title = f"Encounters to Check ({len(encs_to_check)})"
            markdown_content.append(f"<details markdown=\"1\">\n<summary>{encounters_title}</summary>\n\n")

            for enc_key, enc_check_data in encs_to_check.items():
                # Count number of types to check for this encounter
                review_count = len(enc_check_data['types'])

                encounter_title = f"Encounter: {enc_check_data['num']} (Status: {enc_check_data['clm_status']}, Review: {review_count})"
                markdown_content.append(f"<details markdown=\"1\">\n<summary>{encounter_title}</summary>\n\n")

                # Add encounter analysis summary
                for enc_type, cpt4_list in enc_check_data['types'].items():
                    cpt4_str = ", ".join(cpt4_list) if cpt4_list else "No CPT4"
                    markdown_content.append(f"- {enc_type}: {cpt4_str}\n")

                markdown_content.append("\n</details>\n\n")

            markdown_content.append("</details>\n\n")

    def generate_summary_stats(self, data_object: Dict, missing_encounter_efts: Optional[List[str]] = None) -> Dict:
        """
        Generate summary statistics from the data object.

        Args:
            data_object (Dict): Complete data object
            missing_encounter_efts (List[str], optional): List of EFT NUMs with missing encounters

        Returns:
            Dict: Summary statistics
        """
        stats = {
            'total_efts': len(data_object),
            'split_efts': 0,
            'not_split_efts': 0,
            'total_payments': 0,
            'total_encounters': 0,
            'total_encounters_to_check': 0,
            'missing_encounter_efts': len(missing_encounter_efts) if missing_encounter_efts else 0,
            'payer_name': self.payer_name,
            'payment_statuses': {},  # Track payment status counts
            'not_split_by_status': {}  # Track not-split payments by status
        }

        for eft in data_object.values():
            if eft['is_split']:
                stats['split_efts'] += 1
            else:
                stats['not_split_efts'] += 1

            stats['total_payments'] += len(eft['payments'])

            for payment in eft['payments'].values():
                stats['total_encounters'] += len(payment['encounters'])
                stats['total_encounters_to_check'] += len(payment.get('encs_to_check', {}))

                # Track payment status counts
                payment_status = payment.get('status', 'Unknown')
                if payment_status not in stats['payment_statuses']:
                    stats['payment_statuses'][payment_status] = 0
                stats['payment_statuses'][payment_status] += 1

                # Track not-split payments by status
                if not eft['is_split']:
                    if payment_status not in stats['not_split_by_status']:
                        stats['not_split_by_status'][payment_status] = 0
                    stats['not_split_by_status'][payment_status] += 1

        return stats