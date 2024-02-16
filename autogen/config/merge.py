import json
from autogen.config.shared.utils.instructions import SYSTEM_INSTRUCTION

def deep_merge(dict1, dict2):
    """
    Perform a deep merge of two dictionaries.
    If a key maps to a list in both dictionaries, the lists are concatenated.
    """
    for key in dict2:
        if key in dict1:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                deep_merge(dict1[key], dict2[key])
            elif isinstance(dict1[key], list) and isinstance(dict2[key], list):
                dict1[key] = dict1[key] + dict2[key]
            else:
                dict1[key] = dict2[key]
        else:
            dict1[key] = dict2[key]
    return dict1


def merge_json_configs(file1, file2, output_file):
    """
    Merge two JSON configurations by performing a deep merge.

    Args:
    file1 (str): File path to the first JSON configuration.
    file2 (str): File path to the second JSON configuration.
    output_file (str): File path for the merged JSON configuration output.

    Returns:
    None: The merged configuration is saved to the specified output file.
    """
    # Read the first JSON file
    with open(file1, "r") as f:
        config1 = json.load(f)

    # Read the second JSON file
    with open(file2, "r") as f:
        config2 = json.load(f)

    # Perform a deep merge
    merged_config = deep_merge(config1, config2)

    # Write the merged configuration to the output file
    with open(output_file, "w") as f:
        json.dump(merged_config, f, indent=4)

    print(f"Merged configuration saved to {output_file}")


# # Example usage
# merge_json_configs(
#     "shared/agents.json",
#     "custom_apps/financial_bot/config.json",
#     "merged_config.json",
# )
