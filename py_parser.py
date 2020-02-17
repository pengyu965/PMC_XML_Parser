from bs4 import BeautifulSoup
import os
import shutil
import re
import json
import spacy
from nltk import tokenize
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters
import sys
import unidecode

nlp = spacy.load('en_core_web_sm')

class nxmlParser():
    def __init__(self):
        self.filename = ""
        self.tags_list = ["fig", "table"]
        # refID_attr is used to indicate the image refered by rid is a 
        # table or figure
        self.refID_attr = {}
        
        # Reference markerKey_uid is used to find the sentences and link this sentences to unique id
        # which would be showed in brat (replace the num)
        self.refMarkerkey_refID = {}

        self.capMarkerkey_refID = {}

        self.refID_list = []
        # uid_refID is used to make markerkey --> refID --> uid, a closed circle
        self.refID_uid = {}

        # dref_json is a json file stores all direct reference with uid
        self.dref_json = []

        # caption_json is a json file stores all captions with corresponded uid
        self.caption_json = []

        # tableXML_json is used for storing the table xml format because 
        # the table is not given by image format
        self.refID_imgXML = {}

        # Final saved json
        self.file_json = {}
        self.file_json["refID_uid"] = self.refID_uid
        self.file_json["refID_attr"] = self.refID_attr
        self.file_json["dref_json"] = self.dref_json
        self.file_json["caption_json"] = self.caption_json 
        self.file_json["imgXML_json"] = self.refID_imgXML

    def breakblankRemover(self, txtfile):
        txtfile = unidecode.unidecode(txtfile)
        nobreakline_txt = re.sub("[\n\r\t]", " ", txtfile)
        reduce_blank_txt = re.sub(" +", " ", nobreakline_txt)
        # print(reduce_blank_txt)
        reduce_blank_txt = str.encode(reduce_blank_txt)
        open(tmp_dir + "/nobreakblank.txt", 'wb').write(reduce_blank_txt)
        afterRemover_txt = open(tmp_dir + "/nobreakblank.txt", 'r').read()
        # writing and re-reading prevent small difference in brat 'rU' span error
        return afterRemover_txt

    def segmentPureText(self, txtfile):
        punkt_param = PunktParameters()
        abbreviation = [
            "U.S.A", "u.s.a", "figure", "fig", "Table", "table", "Eq", "eq", 
            "equation", "et al","e.g", "i.e","Fig", "s.d", "etc", "i.v"
            ]
        punkt_param.abbrev_types = set(abbreviation)
        tokenizer = PunktSentenceTokenizer(punkt_param)
        tokenized_output = tokenizer.tokenize(txtfile)
        # print(tokenized_output)

        return tokenized_output

    def title_process(self):
        for title in soup.find_all("title"):
            title.string = "\n" + title.text + ".\n"

    def refID_uid_process(self):
        for ref in soup.find_all("xref"):
            if ref["ref-type"] in ("table", "fig"):
                refID = ref["rid"]
                if refID not in self.refID_list:
                    self.refID_list.append(refID)
                    if ref["ref-type"] == "table":
                        self.refID_attr[refID] = "Table"
                    elif ref["ref-type"] == "fig":
                        self.refID_attr[refID] = "Figure"

        for cap in soup.find_all("fig"):
            refID = cap["id"]
            if refID not in self.refID_list:
                self.refID_list.append(refID)
                self.refID_attr[refID] = "Figure"
        
        for cap in soup.find_all("table-wrap"):
            refID = cap["id"]
            if refID not in self.refID_list:
                self.refID_list.append(refID)
                self.refID_attr[refID] = "Table"

        # Creat the uid which is 1-1 matched with refID
        uid = 1
        for refID in self.refID_list:
            self.refID_uid[refID] = uid
            uid += 1

    
    def addMarkersToReference(self):
        count = 1
        for ref in soup.find_all("xref"):
            # only count and add marker to table or fig
            try:
                ref["ref-type"]
            except KeyError:
                ref["ref-type"] = "NoRef"

            if ref["ref-type"] in ("table", "fig"):
                # marker_key is #directreference-head#{uid.:05}#
                marker_key = '#directreference-head#{:05}#'.format(count)

                if ref.string is None:
                    ref.string = marker_key
                else:
                    ref.string = ref.string + marker_key

                refID = ref["rid"]

                self.refMarkerkey_refID[marker_key] = refID

                count +=1 

    def getDirectReferences(self, sents_list):
        # get direct references and remove the direct references mark 
        # in the text or sentences list
        for idx, sent in enumerate(sents_list): 

            if "#directreference-head#" in sent:
                # Handle one sent has multi marker
                sameSent_Marker = []
                while(True):
                    if "#directreference-head#" in sent:
                        marker = sent[sent.find("#directreference-head#"):sent.find("#directreference-head#")+28]
                        sameSent_Marker.append(marker)
                        sent = sent.replace(marker,'')
                        sents_list[idx] = sent
                    else:
                        break
                # print(sameSent_Marker)
                for marker in sameSent_Marker:
                    drsent_dic = {}
                    refID = self.refMarkerkey_refID[marker]
                    refID_attr = self.refID_attr[refID]

                    drsent_dic["uid"] = self.refID_uid[refID]
                    drsent_dic["Type"] = refID_attr
                    drsent_dic["Text"] = sent
                    drsent_dic["refID"] = refID

                    self.dref_json.append(drsent_dic)
        # print(sents_list)
        # print(json.dumps(self.dref_json,indent=4))
        return sents_list

        ## The sents_list now is without direct reference marker anymore.

    # Complete this two functions later to add caption markers to 
    # self.capMarkerkey_refID --->  self.refID_attr
    # self.capMarkerkey_refID ---> self.refID_uid
    def addMarkersToCaption(self):
        count = 1
        for fig_cap in soup.find_all('fig'):
            # print(fig_cap.label)
            cap_refID = fig_cap["id"]
            self.refID_imgXML[cap_refID] = fig_cap.graphic["xlink:href"]
            st_marker_key = '#caption-start-head#{:05}#'.format(count)
            ed_marker_key = '#caption-ended-head#{:05}#. '.format(count)
            
            if fig_cap.label.text[-1] in (":", "."):
                fig_cap.label.string = st_marker_key + fig_cap.label.text
            else:
                fig_cap.label.string = st_marker_key + fig_cap.label.text + ":"
            
            # print(fig_cap)
            # print(fig_cap.caption.p.text)
            fig_cap.caption.p.string = fig_cap.caption.p.text + ed_marker_key
            
            self.capMarkerkey_refID[st_marker_key] = cap_refID
            
            count += 1
        # self.refID_attr could be reused here in future to tell what attribute of each cap is.
        # refID is always the core key
        for table_cap in soup.find_all('table-wrap'):
            cap_refID = table_cap["id"]
            self.refID_imgXML[cap_refID] = table_cap
            st_marker_key = '#caption-start-head#{:05}#'.format(count)
            ed_marker_key = '#caption-ended-head#{:05}#. '.format(count) 

            if table_cap.label.text[-1] in (":", "."):
                table_cap.label.string = st_marker_key + table_cap.label.text
            else:
                table_cap.label.string = st_marker_key + table_cap.label.text + ":"
            
            table_cap.caption.p.string = table_cap.caption.p.text + ed_marker_key

            self.capMarkerkey_refID[st_marker_key] = cap_refID

    def getCaptions(self, sents_list):
        # get caption and remove the caption mark 
        # in the text or sentences list
        total_sent = len(sents_list)
        for idx, st_sent in enumerate(sents_list):
            cap_sents = []
            cap_dic = {}
            # Sometimes caption-start-head just adhersed to the previous sentences (actually title string) and can't be separate.
            # Which is the reason we need to process the title first.
            if '#caption-start-head#' in st_sent:
                st_marker = st_sent[st_sent.find("#caption-start-head#"):st_sent.find("#caption-start-head#")+26]
                st_sent = st_sent.replace(st_marker, '')
                sents_list[idx] = st_sent
                for idi in range(idx, total_sent):
                    # The first sent looping here are the same sent of st_sent
                    if '#caption-ended-head#' not in sents_list[idi]:
                        cap_sents.append(sents_list[idi])
                    else:
                        ed_marker = sents_list[idi][sents_list[idi].find("#caption-ended-head#"):sents_list[idi].find("#caption-ended-head#")+28]
                        sents_list[idi] = sents_list[idi].replace(ed_marker, '')
                        cap_sents.append(sents_list[idi])
                        break

                cap_refID = self.capMarkerkey_refID[st_marker]
                cap_dic["uid"] = self.refID_uid[cap_refID]
                cap_dic["Type"] = self.refID_attr[cap_refID]
                cap_dic["Text"] = cap_sents
                cap_dic["refID"] = cap_refID

                self.caption_json.append(cap_dic)

        # print(self.caption_json)
        # print(self.file_json)

        return sents_list


    def getSpan_writeTxt(self, sents_list, finalTxt_path):
        # Calculate the caption span with caption json
        with open(finalTxt_path, 'w') as f:
            for sent in sents_list:
                f.write(sent +"\n")
        
        finalTxt = open(finalTxt_path, 'r').read()

        for item in self.dref_json:
            item_sent = item["Text"]
            item_sent_length = len(item_sent)
            
            span_st = finalTxt.find(item_sent)
            span_ed = span_st + item_sent_length 

            item["Span"] = [span_st, span_ed]

            if span_st == -1:
                with open(log_dir + filename + ".txt", 'w') as f:
                    f.write(item_sent+"\n")

        # Calculate the caption span with caption json


    def writeANN(self, finalANN_path):
        t_num = 1
        a_num = 1
        with open(finalANN_path, "w") as f:
            for item in self.dref_json:
                T_line = "T{}\tReference {} {}\t{}\n".format(t_num, item["Span"][0], item["Span"][1], item["Text"])
                f.write(T_line)

                A1_line = "A{}\tRefType T{} Direct\n".format(a_num, t_num)
                a_num += 1
                f.write(A1_line)

                A2_line = "A{}\tType T{} {}\n".format(a_num,t_num,item["Type"])
                a_num += 1
                f.write(A2_line)

                A3_line = "A{}\tUID T{} {}\n".format(a_num, t_num, item["uid"])
                a_num += 1
                f.write(A3_line)

                t_num += 1
























'''
---------------------------------------------------------------------------------------------------------------------
---------------------------------------------------------------------------------------------------------------------
                                            DRIVER'S CODE
---------------------------------------------------------------------------------------------------------------------
---------------------------------------------------------------------------------------------------------------------
''' 


rootdir = './sample_data/'
img_ext = ('.jpg', '.gif', '.png', '.tif')

des_dir = "./PMC/"
tmp_dir = "./tmp/"

log_dir = "./log/"

if not os.path.exists(des_dir):
    os.mkdir(des_dir)
if not os.path.exists(tmp_dir):
    os.mkdir(tmp_dir)
if not os.path.exists(log_dir):
    os.mkdir(log_dir)

unsuccess_list = []

for subdir in os.listdir(rootdir):
    # subdir = "PMC116597"
    # subdir = 'PMC140010'
    # subdir = 'PMC151193'
    print('\nBegined processing file: ', subdir, '\n')
    subdir_path = os.path.join(rootdir, subdir)
    for curr_file in os.listdir(subdir_path):
        curr_file_path = os.path.join(subdir_path, curr_file)

        curr_subdir = des_dir + subdir
        currPath = des_dir + subdir + "/annotation/"
        currImgPath = des_dir + subdir + "/images/"

        if not os.path.exists(curr_subdir):
            os.mkdir(curr_subdir)
        if not os.path.exists(currPath):
            os.mkdir(currPath)
        if not os.path.exists(currImgPath):
            os.mkdir(currImgPath)

        if curr_file.lower().endswith('.nxml'):  
            infile = open(curr_file_path, "r")
            soup = BeautifulSoup(infile, 'xml')

            filename = os.path.splitext(curr_file)[0]
            
            curr_doc = nxmlParser()
            curr_doc.filename = filename

            # Process title to add period and \n at the begining and end, in case
            # it adhersive to the front and behind text
            curr_doc.title_process()

            # Statistically count all the refID <--> attribute, and create the 1 to 1 refID --> uid
            curr_doc.refID_uid_process()
            
            # Add Marker to Reference
            curr_doc.addMarkersToReference()

            # Add Marker to caption
            curr_doc.addMarkersToCaption()
            
            # Get pure text
            parsed_doc_text = soup.get_text()

            # Remove all the \n \r and multi blank and form it into a nearly perfect whole paragraph
            parsed_doc_text = curr_doc.breakblankRemover(parsed_doc_text)

            # Segment the text into sentences level
            sentences_list = curr_doc.segmentPureText(parsed_doc_text)
            
            # Get direct reference and captions
            sentences_list = curr_doc.getDirectReferences(sentences_list)
            sentences_list = curr_doc.getCaptions(sentences_list)

            # Creating the final txt file. 
            # Find the corresponded span
            curr_doc.getSpan_writeTxt(sentences_list, currPath + filename + ".txt")

            curr_doc.writeANN(currPath + filename + ".ann")


        if curr_file.lower().endswith(('png', 'jpg', 'tif', 'gif', 'mov', 'mp4')):
            shutil.copy2(curr_file_path, currImgPath)
        if curr_file.lower().endswith(('nxml', 'xml', 'pdf')):
            shutil.copy2(curr_file_path, curr_subdir)

    print('\nFinished processing file: ', subdir, '\n')
    print('----------------------------------------\n')

    # break