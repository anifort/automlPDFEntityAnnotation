Generate structure for import on AutoML and upload to GCS

- **Ensure there are no pdfs with same name if you are pulling from different folders**
- **Ensure bucket is empty or that you do not mind overwritting existing files with same filename**
```
export BUCKET=gs://aniftos-example-dataset/automl_import_example/
python2.7 input_helper_v2.py -v -s train,train/*.pdf validation,val/*.pdf test,test/*.pdf -t ${BUCKET}
```

upload using the ul,
export using the ui

```
gsutil cp -r gs://aniftos-example-dataset/automl_export_example/* download

```


run the script as with the following parameters:
- -i   :   Path to exported .csv file 
    - i.e gs://bucket/export_path/text_extraction.csv
- -t : Target path, 
    - i.e gs://bucket/annotated_data_export_path
- -d : CSV dictionary file from local path term,LABEL,Mathcing mode [I for IGNORE CASES, R for Regular Expression and E for Exact Match]
    - i.e See dicitonary.csv for example
    
```
python dictionary_tagger.py -i gs://aniftos-example-dataset/automl_export_example/export_data-test_import_entity-2020-04-09T13:39:13.950Z/text_extraction.csv -t gs://aniftos-example-dataset/automl_export_example/t1/ -d dictionary.csv 
```