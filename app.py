from flask import Flask, render_template, request, flash, redirect, url_for, logging
import requests
import re
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key'


UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

easylist_set = set()  # Global variable to store the EasyList set
charles_df = pd.DataFrame() # Global variable to the uploaded file 
filtered_network_calls_df = pd.DataFrame()  # Global variable to store filtered network calls

# New global variables for custom filtering
prebuilt_set = set()  # Replace this with your prebuilt set
# custom_save_path = 'additional_ssp_list.txt'  # File where results are being compiled after being filtered
custom_filtered_network_calls_df = pd.DataFrame()
file_path = 'additional_ssp_List.txt'

def load_file(file_path):
    global charles_df
    try:
        charles_df = pd.read_csv(file_path)
        return charles_df
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

def generate_easy_list_set():
    easylist_url = "https://easylist.to/easylist/easylist.txt"
    easylist_response = requests.get(easylist_url)
    easylist_content = easylist_response.text

    # Extract matches directly into a set, considering '^', '&', or end of the line
    easylist_patterns = set(match.group(1) for match in re.finditer(r"^\|\|([^\^\$&]+)[\^\$&]?[^\S\n]*$", easylist_content, re.MULTILINE) if not match.group().startswith("@@||"))

    # Save the set to a file
    with open('easylist_objects.txt', 'w') as file:
        for obj in easylist_patterns:
            file.write(obj + '\n')

    return easylist_patterns


def generate_ad_network_output():
    global filtered_network_calls_df, charles_df
    if charles_df.empty:
        flash('Error: Charles DataFrame is empty. Please upload a file first.', 'danger')
        return redirect(url_for('index'))

    # Filter network calls based on EasyList patterns
    filtered_network_calls_df = charles_df[charles_df['URL'].apply(lambda url: any(substring in easylist_set for substring in generate_substrings(generate_substring_for_url(url))))]

    # Save the filtered network calls to a separate CSV file
    filtered_log_path = 'filtered_network_calls.csv'  # Adjust the desired path
    filtered_network_calls_df.to_csv(filtered_log_path, index=False)

    flash('Ad network output generated successfully.', 'success')
    return redirect(url_for('index'))

def generate_substrings(input_str):
    return [input_str[i:j] for i in range(len(input_str)) for j in range(i + 1, len(input_str) + 1)]

def generate_substring_for_url(url):
    prefixes = ["https://", "http://"]
    endings = [".com", ".co.in", ".org", ".net"]  # Add more endings if needed

    for prefix in prefixes:
        if url.startswith(prefix):
            url = url[len(prefix):]
            break

    question_mark_index = url.find("?")

    if question_mark_index != -1:
        substring = url[:question_mark_index]
    else:
        for ending in endings:
            index = url.find(ending)
            if index != -1:
                substring = url[:index] + ending
                break
        else:
            substring = url

    return substring

def resetfilter():
    global prebuilt_set, custom_filtered_network_calls_df, charles_df
    if charles_df.empty:
        flash('Error: Charles DataFrame is empty. Please upload a file first.', 'danger')
        return redirect(url_for('index'))
    # app.logger.debug(charles_df.columns)
    if not prebuilt_set:
        # Empty the DataFrame by dropping all rows
        custom_filtered_network_calls_df = pd.DataFrame(columns = charles_df.columns)
        log_path = 'custom_filtered_network_calls.csv'
        custom_filtered_network_calls_df.to_csv(log_path, index=False)
        return
    # Filter rows based on substring presence in the adblock regex set
    custom_filtered_network_calls_df = charles_df[charles_df['URL'].apply(lambda url: any(substring in prebuilt_set for substring in generate_substrings(generate_substring_for_url(url))))]
    log_path = 'custom_filtered_network_calls.csv'
    custom_filtered_network_calls_df.to_csv(log_path, index=False)
    return

def add_to_set_and_file(input_string):
    app.logger.debug(f"before addition Global Data: {prebuilt_set}")
    global custom_filtered_network_calls_df
    if input_string not in prebuilt_set:
        global file_path
        prebuilt_set.add(input_string)
        with open(file_path, 'a') as file:
            file.write(input_string + '\n')
        resetfilter()
        app.logger.debug(f"After addition Global Data: {prebuilt_set}")
    return

def delete_from_set_and_file(input_string):
    app.logger.debug(f"Before deletion Global Data: {prebuilt_set}")
    global custom_filtered_network_calls_df
    if input_string in prebuilt_set:
        global file_path
        prebuilt_set.remove(input_string)
        with open(file_path, 'r') as file:
            lines = file.readlines()
        with open(file_path, 'w') as file:
            for line in lines:
                if line.strip() != input_string:
                    file.write(line)
        resetfilter()
        app.logger.debug(f"After deletion Global Data: {prebuilt_set}")
    return


@app.route('/', methods=['GET', 'POST'])
def index():
    # file_path, custom_filtered_network_calls_df, filtered_network_calls_df, prebuilt_set, easylist_set
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                global charles_df
                charles_df = load_file(file_path)
                if charles_df is not None:
                    print(f"File '{file.filename}' has been uploaded successfully!")

    return render_template('index.html')

@app.route('/generate_easy_list', methods=['POST'])
def generate_easy_list():
    global easylist_set
    easylist_set = generate_easy_list_set()
    flash('Operation successful', 'success')
    return redirect(url_for('index'))  # Redirect to the home directory


@app.route('/generate_ad_network_output', methods=['POST'])
def generate_ad_network_output_route():
    return generate_ad_network_output()


@app.route('/add_to_set_and_file', methods=['POST'])
def add_to_set_and_file_route():
    global  prebuilt_set, charles_df
    app.logger.debug(f"Set initially : {prebuilt_set}")
    if charles_df.empty:
        flash('Error: Charles DataFrame is empty. Please upload a file first.', 'danger')
        return redirect(url_for('index'))
    input_string = request.form.get('input_string')
    if len(input_string) == 0:
        flash('Error: Please enter a string', 'danger')
        return redirect(url_for('index'))
    lower_input_string = input_string.lower()
    add_to_set_and_file(lower_input_string)
    flash(f'Success: Added "{lower_input_string}" to the set and file.', 'success')
    return redirect(url_for('index'))

@app.route('/delete_from_set_and_file', methods=['POST'])
def delete_from_set_and_file_route():
    global  prebuilt_set, charles_df
    if charles_df.empty:
        flash('Error: Charles DataFrame is empty. Please upload a file first.', 'danger')
        return redirect(url_for('index'))
    input_string = request.form.get('input_string')
    if len(input_string) == 0:
        flash('Error: Please enter a string', 'danger')
        return redirect(url_for('index'))
    lower_input_string = input_string.lower()
    delete_from_set_and_file(lower_input_string)
    flash(f'Success: Deleted "{lower_input_string}" from the set and file.', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
