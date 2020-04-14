# ==========================================================================================
# MIT License
#
# Copyright (c) 2020 Christos Aniftos
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==========================================================================================
import json, csv, re
from google.cloud import storage
from io import StringIO
import argparse



def load_dictionary(dictionarypath):
    if not dictionarypath.endswith('.csv'):
        raise Exception('input file should be a .csv')
    d = {}
    with open(dictionarypath) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            d[row[0]] = (row[1],row[2])
    return d


def processLine(line, dictionary) :

    j = json.loads(line)

    j["annotations"] = []  # IF KEY EXISTS , IT WILL REPLACE IT

    content = j['document']['documentText']['content']

    for k, v in dictionary.items():
        label = v[0]
        matching_mode = v[1].lower()
        matcher = []
        if matching_mode == 'e':
          # Exact match word on the boundary
          regex = u'\\b(%s)\\b' % re.escape(k)
          matcher = re.finditer(regex, content, re.UNICODE)
        elif matching_mode == 'i':
          # Ignore case match word on the boundary
          regex = u'\\b(%s)\\b' % re.escape(k)
          matcher = re.finditer(regex, content, re.UNICODE | re.IGNORECASE)
        elif matching_mode == 'r':
          # Use regex to match word (not necessarily on word boundary)
          regex = u'(%s)' % k
          matcher = re.finditer(regex, content, re.UNICODE)


        for m in matcher:
            annot = {}
            annot['displayName'] = label
            annot['textExtraction'] = {}
            annot['textExtraction']['textSegment'] = {}
            annot['textExtraction']['textSegment']['startOffset'] = m.span()[0]
            annot['textExtraction']['textSegment']['endOffset'] = m.span()[1]

            j["annotations"].append(annot)

    return json.dumps(j)


def process_documents(from_gspath, to_gspath, dictionarypath):
    dictionary = load_dictionary(dictionarypath)

    if not from_gspath.startswith('gs://'):
        raise Exception('input file should be a gs:// path')

    if not from_gspath.endswith('.csv'):
        raise Exception('input file should be a .csv')

    if not to_gspath.startswith('gs://'):
        raise Exception('input file should be a gs:// path')

    if to_gspath.endswith('/'):
        to_gspath=to_gspath[:-1]

    storage_client = storage.Client()


    from_patharr = from_gspath.split("/")
    from_bucket = from_patharr[2]
    from_prefix_path = '/'.join(from_patharr[3:])
    from_bucket_obj = storage_client.get_bucket(from_bucket)



    to_patharr = to_gspath.split("/")
    to_bucket = to_patharr[2]
    to_prefix_path = '/'.join(to_patharr[3:])
    to_bucket_obj = storage_client.get_bucket(to_bucket)


    from_blob = from_bucket_obj.blob(from_prefix_path)
    csv_file_str = from_blob.download_as_string().decode('utf-8')
    f = StringIO(csv_file_str)
    reader = csv.reader(f, delimiter=',')

    csv_buffer = ""
    for row in reader:
        type_set = row[0]
        location = row[1]


        location_patharr = location.split("/")
        location_bucket = location_patharr[2]
        location_prefix_path = '/'.join(location_patharr[3:])
        location_bucket_obj = storage_client.get_bucket(location_bucket)

        location_blob = location_bucket_obj.blob(location_prefix_path)
        if not location_prefix_path.endswith('.jsonl'):
            raise Exception('a none .jsonl file path found in inmported CSV')

        filestr = location_blob.download_as_string().decode('utf-8')

        write_buffer = ""

        for line in filestr.splitlines():
            tagged_line = processLine(line, dictionary)
            write_buffer += "{}\n".format(tagged_line)


        blob_write = storage.Blob("{}/{}".format(to_prefix_path, location_blob.name.split("/")[-1]), to_bucket_obj)

        blob_write.upload_from_string(
            data=(write_buffer),
            content_type='application/json',
            client=storage_client,
        )

        csv_buffer += "{},{}/{}\n".format(type_set, to_gspath, location_blob.name.split("/")[-1])

    blob_write = storage.Blob("{}/{}".format(to_prefix_path, from_blob.name.split("/")[-1]), to_bucket_obj)


    blob_write.upload_from_string(
            data=(csv_buffer),
            content_type='application/json',
            client=storage_client,
    )







if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i',
        '--input_gcs_csv_path',
        help='The GCS path to input csv, as it was exported by AutoML NP Etrity export, e.g. gs://bucket/text_extraction.csv.',
        required=True
    )
    parser.add_argument(
        '-t',
        '--target_gcs_directory',
        help='The GCS directory to upload the generated jsonl files and csv.',
        required=True)

    parser.add_argument(
        '-d',
        '--dictionary',
        help='The dictionary in csv to annotation data. Each line contains a '
             '"pattern,label[,mode]" . Import this from local path(not GCS)', required=True)

    args = parser.parse_args()

    process_documents(args.input_gcs_csv_path, args.target_gcs_directory, args.dictionary)