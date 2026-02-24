import boto3
import os
import glob
from pathlib import Path
from collections.abc import Iterable 

# from Classes.Base.S3 import S3
from Classes.Base import Config

class SyncS3():
    def __init__(self):
        #S3.__init__(self)
        self.resource = boto3.resource(
        "s3",
        aws_access_key_id=Config.S3_KEY,
        aws_secret_access_key=Config.S3_SECRET
        )

        self.client = boto3.client(
            's3',
            aws_access_key_id=Config.S3_KEY,
            aws_secret_access_key=Config.S3_SECRET
        )

    def getCasesSyncInit(self):
        try:
            my_bucket = self.resource.Bucket(Config.S3_BUCKET)
            result = my_bucket.meta.client.list_objects(Bucket=my_bucket.name, Delimiter='/')
            if isinstance(result.get('CommonPrefixes'), Iterable):
                cases = [ f.get('Prefix')[:-1] for f in result.get('CommonPrefixes')]
            else:
                cases = []
            return cases
        except(IOError):
            raise IOError

    def downloadSync(self, prefix, local, bucket):
        """
        params:
        - prefix: pattern to match in s3; case name
        - local: local path to folder in which to place files
        - bucket: s3 bucket with target contents
        - client: initialized s3 client object
        """
        client=self.client
        keys = []
        dirs = []
        next_token = ''
        base_kwargs = {
            'Bucket':bucket,
            'Prefix':prefix,
        }
        while next_token is not None:
            kwargs = base_kwargs.copy()
            if next_token != '':
                kwargs.update({'ContinuationToken': next_token})
            results = client.list_objects_v2(**kwargs)
            contents = results.get('Contents')
            for i in contents:
                k = i.get('Key')
                if k[-1] != '/':
                    keys.append(k)
                else:
                    dirs.append(k)
            next_token = results.get('NextContinuationToken')
        for d in dirs:
            dest_pathname = os.path.join(local, d)
            if not os.path.exists(os.path.dirname(dest_pathname)):
                os.makedirs(os.path.dirname(dest_pathname))
        for k in keys:
            dest_pathname = os.path.join(local, k)
            if not os.path.exists(os.path.dirname(dest_pathname)):
                os.makedirs(os.path.dirname(dest_pathname))
            client.download_file(bucket, k, dest_pathname)

    #s3.uploadSync(localDir, case, Config.S3_BUCKET, '*')
    def uploadSync(self, localDir, awsInitDir, bucketName, tag, prefix=os.sep):
        """
        from current working directory, upload a 'localDir' with all its subcontents (files and subdirectories...)
        to a aws bucket
        Parameters
        ----------
        localDir :   localDirectory to be uploaded
        awsInitDir : prefix 'directory' in aws
        bucketName : bucket in aws
        tag :        tag to select files, like *png
                    NOTE: if you use tag it must be given like --tag '*txt', in some quotation marks... for argparse
        prefix :     to remove initial '/' from file names

        Returns
        -------
        None
        """
        resource = self.resource
        # mydirs daje listu svvih file i folder u localDir npr WebApp/DataStorage/Demo/genData.json
        mydirs = list(localDir.glob('**'))
        for mydir in mydirs:
            dirNames = glob.glob(os.path.join(mydir, tag))
            fileNames = [f for f in dirNames if not Path(f).is_dir()]
            #rows = len(fileNames)
            for i, FullfileName in enumerate(fileNames):
                #dobijemo ime file npr, genData.json
                fileName = str(FullfileName).replace(str(localDir), '')
                if fileName.startswith(prefix):  # only modify the text if it starts with the prefix
                    fileName = fileName.replace(prefix, "", 1) # remove one instance of prefix
                    fileName = fileName.replace(os.sep, '/')

                awsPath = str(awsInitDir) + '/' + str(fileName)
                resource.meta.client.upload_file(FullfileName, bucketName, awsPath)

    def deleteSync(self, case):
        try:
            my_bucket = self.resource.Bucket(Config.S3_BUCKET)
            my_bucket.objects.filter(Prefix=case+"/").delete()
        except(IOError):
            raise IOError

    def updateSync(self, localFile, awsInitDir, bucketName):
        """
        upload a 'localFile' 
        to a aws bucket
        Parameters
        ----------
        localFile :   localFile to be uploaded
        awsInitDir : prefix 'directory' in aws
        bucketName : bucket in aws
        Returns
        -------
        None
        """
        resource = self.resource
        fileName = localFile.name
        localFile = str(localFile).replace(os.sep, '/')
        if awsInitDir != '':
            awsPath = str(awsInitDir) + '/' + str(fileName)
        else:
            awsPath = str(fileName)
        resource.meta.client.upload_file(localFile, bucketName, awsPath)