#!/usr/bin/python3

import os,shutil,json,datetime,collections,linecache,re,argparse


class planBuilder():
    '''Creates a plan page from a list of tagged wiki files,
    based on the contents of a tags file.'''


    def __init__(self,conf_file,date=False):
        # Generate a date object for tag calculation
        if date:
            # Split date string at each dash, 
            # reverse the order of members and convert to integer
            fmtdate = date.split("-")
            fmtdate.reverse()
            a = list()
            for i in fmtdate:
                a.append(int(i))
            self.date=datetime.date(*a)
        else:
            self.date=datetime.date.today()
        self.target_file = self.date.strftime("%Y-%m-%d") + ".wiki"
        self.config_file = conf_file
        self.read_config()
        self.build_list()
        self.tag_search()

    def read_config(self):
        '''Reads the contents of a json configuration file'''
        with open(self.config_file) as src:
            config_data = json.load(src)
            self.config = config_data["config"]
        # The root directory of the vimwiki files
        self.wiki_path = os.path.expandvars(self.config["wiki_path"])

        # The tags file in the wiki_path
        self.tags_filename = self.config["tags_file"]
        self.tags_file = self.wiki_path + "/" + self.tags_filename

        # Path for temp files generated during the execution of the program
        self.temp_path = self.config["temp_path"]

        # Path, within the wiki_path, of the diary/journal files
        self.diary_dir = self.config["diary_dir"]

        # Target; the file which will be written out at the end of the run
        self.target = self.wiki_path + self.diary_dir + self.target_file

        # Create the list of sections
        self.sections = collections.OrderedDict()
        for k in self.config["sections"]:
            self.sections[k] = collections.OrderedDict()

        # Prepare clean tempfile directory
        if os.path.exists(self.temp_path):
            shutil.rmtree(self.temp_path)
        os.mkdir(self.temp_path)

    def build_list(self):
        '''Build a list of possible tags, based on the contents of the
        json config file and a date stamp'''

        # Begin parsing the tags list from the config json file
        self.tag_list = dict()
        tree = self.config["tags"]
        for t in tree:
            # Read the values set for one tag
            values = tree[t]

            #Interpret a datestring pattern
            if values["model"] == "date":
                datestr = self.date.strftime(values["pattern"])
                tagname = values["leader"] + datestr
            elif values["model"] == "string":
                tagname = values["leader"] + values["pattern"]
            self.tag_list[tagname] = [values["section"], values["display"]]

    def tag_search(self):
        '''Create instances of tag objects, populating the sections dict
        of a planBuilder instance'''
        with open(self.tags_file) as src:
            # Read each line in the tags file
            for line in src:
                # Ignore header
                if line[0] != "!":
                    # Create a tagInstance
                    obj = tagInstance(line,self.wiki_path,self.temp_path) 
                    tag_name = obj.tag_name                              
                    # Process tags that are contained in the configuration file
                    if tag_name in self.tag_list:                        
                        section = self.tag_list[tag_name][0]

                        # Ensure the tag is listed in the appropriate section
                        if tag_name not in self.sections[section]:
                            self.sections[section][tag_name] = list()   
                        obj.display = self.tag_list[tag_name][1]
                        self.sections[section][tag_name].append(obj)

    def temp_gen(self):
        '''Generate the temporary files for all matching tags'''
        for section in self.sections:
            sec_obj = self.sections[section]
            for tag in sec_obj:
                tag_obj = sec_obj[tag]
                for instance in tag_obj:
                    instance.output_gen()

    def compile_plan(self):
        '''Compile the plan for the specified date from all matching temp files'''
        with open(self.target,'w') as target:
            target.write("= " + self.date.strftime("%Y-%m-%d") + " =\n\n")
            for section in self.sections:
                target.write("= " + section + " =\n")
                sec_obj = self.sections[section]
                for tag in sec_obj:
                    with open(self.temp_path + tag + ".tmp") as src:
                        target.write(src.read())
                target.write("\n\n")



class tagInstance():
    
    def __init__(self,input_line,wiki_path,temp_path):
        self.input_line = input_line
        self.wiki_path = wiki_path
        self.temp_path = temp_path
        self.decode_tag()

    def decode_tag(self):
        '''Parse the tags file entry passed into the script'''
        fields = self.input_line.split("\t")
        self.tag_name = fields[0]
        self.filename = fields[1]
        self.linenum = fields[2].replace(';"','')
        desc = fields[3]
        self.description = desc.split("\\t")[1]
        if "#" in self.description:
            self.short_description = self.description.split("#")[1]
        else: 
            self.short_description = self.description
        self.link = "/"+self.description
        self.tmp = self.temp_path + self.tag_name + ".tmp"
       

    def grab_line(self):
        '''Pull in the text of an input line'''
        self.line_text = linecache.getline(self.wiki_path+self.filename, int(self.linenum)).strip()
        self.line_text = self.line_text.replace(":"+self.tag_name+":","")

    def return_line(self):
        '''Return line of text with link to original'''
        link = "[["+self.link.strip()+"|@]]"
        output = re.sub(":[^ ]*:", "",self.line_text+link + "\n")
        return output

    def return_desc(self):
        '''Return link with simplified description'''
        link = "[["+self.link.strip()+"|"+self.short_description.strip()+"]]"
        output = re.sub(":[^ ]*:", "","* " + link + "\n")
        return output

    def return_contents(self):
        '''Return the contents of a tagged file'''
        with open(self.wiki_path + self.filename) as src:
            cont = re.sub(":[^ ]*:", "",src.read())
        return cont
        
    def output_gen(self):
        '''Produce the output from the temp files'''
        #print(self.tag_name)
        #print(self.linenum)
        #print(self.description)
        #print(self.wiki_path + self.filename)
        if self.display =="line":
            self.grab_line()
            with open(self.tmp,'a') as target:
                target.write(self.return_line())
        elif self.display =="description":
            with open(self.tmp,'a') as target:
                target.write(self.return_desc())
        elif self.display =="file":
            with open(self.tmp,'a') as target:
                target.write(self.return_contents())

def main():
    parser = argparse.ArgumentParser(description="Generate a plan page in vimwiki based on tags")
    parser.add_argument('-d', action="store", dest="input_date", default=False)
    parser.add_argument('-c', action="store", dest="config_location", default=False)
    args = parser.parse_args()
    input_date = args.input_date
    config_location = args.config_location

    potential_configs = ["$HOME/.vwplan_conf.json", "/etc/vwplan_conf.json"]
    if not config_location:
        for name in potential_configs:
            filename = os.path.expandvars(name)
            if os.path.exists(filename):
                config_location = filename
                break
    
    plan = planBuilder(config_location, input_date)
    plan.temp_gen()
    plan.compile_plan()

if __name__ == "__main__":
    main()
