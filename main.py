import streamlit as st
import zipfile
import tempfile
import os
import json


def main()
  st.title("Upload Your Hinge Export")
  
  uploaded = st.file_uploader("Upload ZIP file", type=["zip"], accept_multiple_files=False)
  
  if uploaded:
      tmpdir = tempfile.mkdtemp()
      zip_path = os.path.join(tmpdir, "hinge.zip")
      with open(zip_path, "wb") as f:
          f.write(uploaded.getbuffer())
      
      with zipfile.ZipFile(zip_path, "r") as z:
          z.extractall(tmpdir)
  
      json_files = []
      for root, dirs, files in os.walk(tmpdir):
          for file in files:
              if file.endswith(".json"):
                  json_files.append(os.path.join(root, file))
  
      # just print the names, not the contents
      file_names = [os.path.basename(p) for p in json_files]
      st.write("Found JSON files:", file_names)
