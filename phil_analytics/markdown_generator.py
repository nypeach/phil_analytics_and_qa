"""
PHIL Analytics and QA Library - Markdown Generator

This module generates markdown files from the complete data object.
Creates {filename}_efts.md with encounters that need review.
"""

from typing import Dict, List
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

    def generate_efts_markdown(self, data_object: Dict, output_dir: str = ".") -> str:
        """
        Generate {payer}_efts.md file with encounters that need review.

        Args:
            data_object (Dict): Complete data object with all EFTs, payments, encounters
            output_dir (str): Directory to save the markdown file

        Returns:
            str: Path to the saved markdown file
        """
        print(f"📝 Generating EFTs markdown for {self.payer_name}...")

        markdown_content = []
        markdown_content.append(f"# {self.payer_name} EFTs Analysis\n\n")

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
                pla_count = len(payment["plas"]["pla_l6"]) + len(payment["plas"]["pla_other"])

                payment_info = {
                    'payment_key': payment_key,
                    'eft_num': eft_num,
                    'practice_id': payment['practice_id'],
                    'pmt_num': payment['num'],
                    'encs_to_check_count': encs_to_check_count,
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
                    payment_title = f"{payment_info['practice_id']}_{payment_info['pmt_num']} (EFT: {payment_info['eft_num']}, Encs To Check: {payment_info['encs_to_check_count']}, PLAs: {payment_info['pla_count']})"
                    markdown_content.append(f"<details markdown=\"1\">\n<summary>{payment_title}</summary>\n\n")

                    # Add detailed payment content
                    self._generate_payment_details(payment_info['payment'], payment_info['eft'], markdown_content)

                    markdown_content.append("</details>\n\n")
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

                payment_title = f"{payment['practice_id']}_{payment['num']} (Status: {payment_status}, Encs To Check: {encs_to_check_count}, PLAs: {pla_count})"
                markdown_content.append(f"<details markdown=\"1\">\n<summary>{payment_title}</summary>\n\n")

                # Add detailed payment content
                self._generate_payment_details(payment, eft, markdown_content)

                markdown_content.append("</details>\n\n")  # Close payment

            markdown_content.append("</details>\n\n")  # Close EFT

        markdown_content.append("</details>\n\n")  # Close EFTs - Split

    def _generate_payment_details(self, payment: Dict, eft: Dict, markdown_content: List[str]) -> None:
        """
        Generate the detailed content for a payment (PLAs and Encounters).

        Args:
            payment (Dict): Payment object
            eft (Dict): EFT object (for context)
            markdown_content (List[str]): List to append markdown content to
        """
        # PLA section
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

        if not payment["plas"]["pla_l6"] and not payment["plas"]["pla_other"]:
            markdown_content.append("No PLAs found.\n\n")

        markdown_content.append("</details>\n\n")

        # Encounters section - only show encounters that need review
        encs_to_check = payment.get("encs_to_check", {})
        encounters_title = f"Encounters to Check ({len(encs_to_check)})"
        markdown_content.append(f"<details markdown=\"1\">\n<summary>{encounters_title}</summary>\n\n")

        if encs_to_check:
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
        else:
            markdown_content.append("No encounters require review.\n\n")

        markdown_content.append("</details>\n\n")

    def generate_summary_stats(self, data_object: Dict) -> Dict:
        """
        Generate summary statistics from the data object.

        Args:
            data_object (Dict): Complete data object

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