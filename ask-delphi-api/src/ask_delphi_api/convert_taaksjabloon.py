from pathlib import Path
import numpy as np
import pandas as pd
import warnings
import re
import json

def read_dir(dir_path):

    dir = Path(dir_path) # replace with your path
    if not dir.is_dir():
        raise ValueError("taaksjabloon directory not found")

    paths = []
    for path in dir.iterdir():
        if path.is_file():
            print(path.name)
            paths.append(path.absolute())

    return paths

def convert_doc_to_tables(path):

    # This cell of code comes from https://stackoverflow.com/questions/58254609/python-docx-parse-a-table-to-panda-dataframe (slightly modified)

    from docx import Document
    import pandas as pd

    # Load the Word document
    document = Document(path)

    # Initialize an empty list to store tables
    tables = []

    # Iterate through each table in the document
    for table in document.tables:
        # Create a list structure to store all cell values
        data = []
        
        # Iterate through each row in the current table
        for i, row in enumerate(table.rows):
            row_data = []
            # Iterate through each cell in the current row
            for cell in row.cells:
                # Store cell text (or empty string if no text)
                row_data.append(cell.text.strip())
            data.append(row_data)
        
        # Use the first row as column headers and the rest as data
        if data:
            df = pd.DataFrame(data[1:], columns=data[0])
            tables.append(df)

    print(f"retrieved {len(tables)} tables from doc {path}")
    
    return tables

def filter_tables_by_title(table_list, keyword):
    return [table for table in table_list if table.columns[0].lower().startswith(keyword)]

def remove_prefix_ci(text, prefix):
    if text.lower().startswith(prefix.lower()):
        return text[len(prefix):]
    return text

def clean_strip(text):
    result = re.sub(r'^[^a-zA-Z]+', '', text)  # Strip from left
    result = re.sub(r'[^a-zA-Z]+$', '', result)  # Strip from right
    return result

# extraction functions

def extract_digicoach_title(tables):
    title_tables = filter_tables_by_title(tables, "titel")
    if len(title_tables) == 0:
        raise ValueError("No title tables found")
    if len(title_tables) > 1:
        warnings.warn("Multiple title tables found, continuing with the first", UserWarning)
    title = title_tables[0].columns[1]
    print(f"Found title: {title}")
    return title

def extract_digicoach_tags(tables):
    tags = []
    tag_tables = filter_tables_by_title(tables, "tag")
    if len(tag_tables) == 0:
        raise ValueError("No tag tables found")
    if len(tag_tables) > 1:
        warnings.warn("Multiple tag tables found, continuing with the first", UserWarning)
    tag_table = tag_tables[0]
    for i in range(0, len(tag_table.columns), 2):
        sub_table = tag_table.iloc[:,i:i+2]
        hits = sub_table.replace("", np.nan).dropna()
        values = hits.iloc[:,0].to_list()
        if values:
            new_tag = {}
            tag_type = sub_table.columns[0]
            tag_type = remove_prefix_ci(tag_type, "tag")
            tag_type = clean_strip(tag_type)
            new_tag["type"] = tag_type
            new_tag["values"] = values
            for val in values:
                print(f"Found tag: {tag_type} {val}")
            tags.append(new_tag)
    return tags

def extract_digicoach_tasks(tables):
    tasks = []
    task_tables = filter_tables_by_title(tables, "taak")
    if len(task_tables) == 0:
        raise ValueError("No task tables found")
    for table in task_tables:
        new_task = {}
        data = table.iloc[:,1] #only need second column
        data = data.replace("", np.nan).dropna()

        task_name = data.name
        task_name = remove_prefix_ci(task_name, "taak")
        task_name = clean_strip(task_name)
        new_task["name"] = task_name
        new_task["description"] = data[0]

        if not len(data)%2 == 1:
            raise ValueError(f"invalid step_df: {data}")
        
        step_df = pd.DataFrame(
            data.values[1:].reshape(-1,2),
            columns = ["Stap", "Beschrijving"]
        )
        steps = []

        for _, row in step_df.iterrows():
            new_step = {}
            step_name = row["Stap"]
            step_name = remove_prefix_ci(step_name, "stap")
            step_name = clean_strip(step_name)
            new_step["name"] = step_name
            new_step["description"] = row["Beschrijving"]
            steps.append(new_step)
            print(f"Found step: {step_name}")

        new_task["steps"] = steps
        tasks.append(new_task)
        print(f"Found task: {task_name}")
    return tasks

def extract_digicoach_sources(tables):
    sources = []

    source_tables = filter_tables_by_title(tables, "nr")
    
    if len(source_tables) == 0:
        raise ValueError("No source tables found")
    
    for table in source_tables:
        new_source = {}
       
        data = table.iloc[:,[1,2,3]]
        data = data.replace("", np.nan).dropna()
        
        instruction_df = pd.DataFrame(
            data.values.reshape(-1,3),
            columns = ["Titel", "Type", "Link"]
        )

        for _, row in instruction_df.iterrows():
            new_source = {}
            source_titel = row["Titel"]
            source_titel = clean_strip(source_titel)
            new_source["titel"] = source_titel
            new_source["type"] = row["Type"]
            new_source["link"] = row["Link"]
            sources.append(new_source)
        
        print(f"Found sources: {sources}")

    return sources

def convert_doc_to_json(path):
    tables = convert_doc_to_tables(path)
    title = extract_digicoach_title(tables)
    tags = extract_digicoach_tags(tables)
    tasks = extract_digicoach_tasks(tables)
    sources = extract_digicoach_sources(tables)
    digicoach = {"name": title,  "tags": tags, "tasks": tasks, "sources": sources}
    digicoach_json = json.dumps(digicoach, indent=2)
    return digicoach_json