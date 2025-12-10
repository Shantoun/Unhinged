import streamlit as st
import zipfile
import tempfile
import os
import json


def uploader():
    st.title("Upload Your Hinge Export")

    uploaded = st.file_uploader("Upload ZIP file", type=["zip"], accept_multiple_files=False)

    if not uploaded:
        return None  # nothing uploaded yet

    # temp folder
    tmpdir = tempfile.mkdtemp()
    zip_path = os.path.join(tmpdir, "hinge.zip")

    # save uploaded zip
    with open(zip_path, "wb") as f:
        f.write(uploaded.getbuffer())

    # extract zip
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(tmpdir)

    # find JSON files
    json_files = []
    for root, dirs, files in os.walk(tmpdir):
        for file in files:
            if file.endswith(".json"):
                json_files.append(os.path.join(root, file))

    # debug print
    file_names = [os.path.basename(p) for p in json_files]
    st.write("Found JSON files:", file_names)

    # load ALL json files into a dict
    data = {}
    for p in json_files:
        name = os.path.basename(p).replace(".json", "")  # e.g., "matches"
        with open(p, "r") as f:
            data[name] = json.load(f)

    # return all parsed json + tempdir for cleanup
    return {
        "tmpdir": tmpdir,
        "json": data
    }







# def uploader():
#   st.title("Upload Your Hinge Export")
  
#   uploaded = st.file_uploader("Upload ZIP file", type=["zip"], accept_multiple_files=False)
  
#   if uploaded:
#       tmpdir = tempfile.mkdtemp()
#       zip_path = os.path.join(tmpdir, "hinge.zip")
#       with open(zip_path, "wb") as f:
#           f.write(uploaded.getbuffer())
      
#       with zipfile.ZipFile(zip_path, "r") as z:
#           z.extractall(tmpdir)
  
#       json_files = []
#       for root, dirs, files in os.walk(tmpdir):
#           for file in files:
#               if file.endswith(".json"):
#                   json_files.append(os.path.join(root, file))
  
#       # just print the names, not the contents
#       file_names = [os.path.basename(p) for p in json_files]
#       st.write("Found JSON files:", file_names)
