"""
PHIL Analytics and QA Library - Markdown Generator

This module generates markdown files from the complete data object.
Creates {filename}_efts.md with encounters that need review.
"""

from typing import Dict, List, Optional
from pathlib import Path
from collections import defaultdict


class MarkdownGenerator:
    """
    Generates markdown files from the complete data object.
    Creates nested markdown with GitHub-style toggles for encounters that need review.
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

        # Generate main combined file
        main_file_path = self._generate_main_efts_file(data_object, output_dir, missing_encounter_efts, analytics_results)

        return main_file_path

    def _generate_main_efts_file(self, data_object: Dict, output_dir: str, missing_encounter_efts: Optional[List[str]], analytics_results: Optional[Dict]) -> str:
        """Generate the main combined EFTs markdown file."""
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

            # Add link to It Shoulds after Max Encounters section
            self._generate_it_shoulds_link_section(markdown_content)

    def _generate_it_shoulds_link_section(self, markdown_content: List[str]) -> None:
        """
        Generate the link to the "It Shoulds" Notion page.

        Args:
            markdown_content (List[str]): List to append markdown content to
        """
        markdown_content.append("### Link to \"It Shoulds\"\n\n")
        markdown_content.append("[PS1D - PHIL \"It Should\"](https://www.notion.so/thoughtfulautomation/PS1D-PHIL-It-Should-1f8f43a78fa48033931ceded894c60ce)\n\n")

    def _generate_not_split_section(self, not_split_efts: Dict, markdown_content: List[str]) -> None:
        """
        Generate the "EFTs - Not Split" section organized by payment status.
        Uses simple bullet list for Immediate Post and detailed format for others.

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
                    if status == "Immediate Post":
                        # Simple bullet list format for Immediate Post
                        markdown_content.append(f"- {payment_info['practice_id']}_{payment_info['pmt_num']} (EFT: {payment_info['eft_num']})\n")
                    else:
                        # Detailed format for all other payment types
                        markdown_content.append(f"* **{payment_info['practice_id']}_{payment_info['pmt_num']} (EFT: {payment_info['eft_num']})**\n\n")

                        # Add detailed payment content
                        has_plas = payment_info['pla_count'] > 0
                        has_encounters_to_check = payment_info['encs_to_check_count'] > 0

                        if has_plas or has_encounters_to_check:
                            self._generate_detailed_payment_content(payment_info['payment'], markdown_content, has_plas, has_encounters_to_check)

                        markdown_content.append("\n")
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
                pla_count = len(payment["plas"]["pla_l6"]) + len(payment["plas"]["pla_other"])
                payment_status = payment.get("status", "Unknown")

                # Check if there's any content to show
                has_plas = pla_count > 0
                has_encounters_to_check = encs_to_check_count > 0

                if payment_status == "Immediate Post":
                    # Simple bullet list format for Immediate Post in split EFTs
                    markdown_content.append(f"* **{payment['practice_id']}_{payment['num']} (EFT: {eft_num} \"{payment_status}\")**\n")
                else:
                    # Detailed format for all other payment types in split EFTs
                    markdown_content.append(f"* **{payment['practice_id']}_{payment['num']} (EFT: {eft_num} \"{payment_status}\")**\n\n")

                    if has_plas or has_encounters_to_check:
                        self._generate_detailed_payment_content(payment, markdown_content, has_plas, has_encounters_to_check)

                markdown_content.append("\n")

            markdown_content.append("</details>\n\n")  # Close EFT

        markdown_content.append("</details>\n\n")  # Close EFTs - Split

    def _generate_detailed_payment_content(self, payment: Dict, markdown_content: List[str], has_plas: bool, has_encounters_to_check: bool) -> None:
        """
        Generate detailed payment content with proper indentation.

        Args:
            payment (Dict): Payment object
            markdown_content (List[str]): List to append markdown content to
            has_plas (bool): Whether this payment has PLAs
            has_encounters_to_check (bool): Whether this payment has encounters to check
        """
        # PLA section
        if has_plas:
            pla_l6_count = len(payment["plas"]["pla_l6"])
            pla_other_count = len(payment["plas"]["pla_other"])

            markdown_content.append(f"  * **PLAs** (L6: {pla_l6_count}, Other: {pla_other_count})\n\n")

            # Add PLA amount breakdown
            self._generate_pla_amount_breakdown_indented(payment, markdown_content)

            # Add L6 PLAs if present
            if payment["plas"]["pla_l6"]:
                markdown_content.append("    * **L6 PLAs:**\n")
                for pla in payment["plas"]["pla_l6"]:
                    markdown_content.append(f"      * {pla}\n")
                markdown_content.append("\n")

            # Add Other PLAs if present
            if payment["plas"]["pla_other"]:
                markdown_content.append("    * **Other PLAs:**\n")
                for pla in payment["plas"]["pla_other"]:
                    markdown_content.append(f"      * {pla}\n")
                markdown_content.append("\n")

        # Encounters section - removed the parent "Encounters to Check" header
        if has_encounters_to_check:
            encs_to_check = payment.get("encs_to_check", {})

            if has_plas:
                # If we have PLAs, use proper indentation to continue the bullet
                encounter_indent = "  "
                sub_indent = "    "
            else:
                # If no PLAs, start fresh bullet
                encounter_indent = "  "
                sub_indent = "    "

            for enc_key, enc_check_data in encs_to_check.items():
                markdown_content.append(f"{encounter_indent}* **Encounter:** {enc_check_data['num']} (Status: {enc_check_data['clm_status']})\n")

                # Add encounter analysis as sub-bullets
                for enc_type, cpt4_list in enc_check_data['types'].items():
                    cpt4_str = ", ".join(cpt4_list) if cpt4_list else ""
                    if cpt4_str:
                        markdown_content.append(f"{sub_indent}* {enc_type}: {cpt4_str}\n")
                    else:
                        markdown_content.append(f"{sub_indent}* {enc_type}\n")

            markdown_content.append("\n")

    def _generate_pla_amount_breakdown_indented(self, payment: Dict, markdown_content: List[str]) -> None:
        """
        Generate the PLA amount breakdown with proper indentation for nested structure.

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

        # Properly indented 3-line format
        markdown_content.append(f"    * Payment Amount: ${payment_amount:,.2f}\n")
        markdown_content.append(f"    * Other PLAs: ${pla_other_amts:,.2f}\n")
        markdown_content.append(f"    * Ledger Balance: ${ledger_balance:,.2f}\n\n")

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