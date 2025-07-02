"""
PHIL Analytics and QA Library - Markdown Generator

This module generates markdown files from the complete data object.
Creates {filename}_efts.md with encounters that need review.
"""

from typing import Dict, List
from pathlib import Path


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

        # Generate "EFTs - Not Split" section as toggle
        not_split_title = f"EFTs - Not Split ({len(not_split_efts)})"
        markdown_content.append(f"<details markdown=\"1\">\n<summary>{not_split_title}</summary>\n\n")

        for eft_num in sorted(not_split_efts.keys()):
            eft = not_split_efts[eft_num]
            self._generate_eft_analysis_section(eft, eft_num, markdown_content)

        markdown_content.append("</details>\n\n")

        # Generate "EFTs - Split" section as toggle
        split_title = f"EFTs - Split ({len(split_efts)})"
        markdown_content.append(f"<details markdown=\"1\">\n<summary>{split_title}</summary>\n\n")

        for eft_num in sorted(split_efts.keys()):
            eft = split_efts[eft_num]
            self._generate_eft_analysis_section(eft, eft_num, markdown_content)

        markdown_content.append("</details>\n\n")

        # Save markdown file
        output_path = Path(output_dir) / f"{self.payer_name}_efts.md"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(markdown_content))

        print(f"   ✅ EFTs markdown saved to: {output_path}")
        return str(output_path)

    def _generate_eft_analysis_section(self, eft: Dict, eft_num: str, markdown_content: List[str]) -> None:
        """
        Generate the markdown section for a single EFT analysis.

        Args:
            eft (Dict): EFT object with analysis results
            eft_num (str): EFT number
            markdown_content (List[str]): List to append markdown content to
        """
        # Calculate total encounters to check across all payments in this EFT
        total_encs_to_check = 0
        for payment in eft["payments"].values():
            encs_to_check = payment.get("encs_to_check", {})
            total_encs_to_check += len(encs_to_check)

        eft_title = f"EFT: {eft_num} (Payer: {eft['payer']}, Payments: {len(eft['payments'])}, Encs To Check: {total_encs_to_check})"
        markdown_content.append(f"<details markdown=\"1\">\n<summary>{eft_title}</summary>\n\n")

        # Payment level
        for payment_key, payment in eft["payments"].items():
            payment_title = f"Payment: {payment_key} (Practice: {payment['practice_id']}, Num: {payment['num']}, Status: {payment['status']})"
            markdown_content.append(f"<details markdown=\"1\">\n<summary>{payment_title}</summary>\n\n")

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
            'payer_name': self.payer_name
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

        return stats