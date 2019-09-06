# slider

A crawler for downloading lecture content from [ILIAS](https://github.com/ILIAS-eLearning/ILIAS), an Open Source Learning Management System. It is tweaked to work for the University of Mannheim.

## Setup

The following instructions will help you run the program.

### Requirements

You need to have pipenv installed.
```bash
$ pip3 install pipenv
```

Create a virtual environment and install the project dependencies with pipenv:
```bash
$ pipenv install
```

### Run

To run the main program, you have to execute the script from within the `slider/` folder in the repository:

```bash
$ cd slider/
$ pipenv run python crawler.py
```

Before you run the program, familiarize yourself with the command line options by passing `--help`. 

```
$ pipenv run python crawler.py --help
Usage: crawler.py [OPTIONS]

Options:
  -d, --dropbox        Upload files using Dropbox API (requires access token).
  -l, --logall         Log everything to the changelog, not just downloads.
  -m, --mail           Send an email if there are new downloads.
  -x, --maxsize FLOAT  Define the maximum size of a file to be downloaded.
  --help               Show this message and exit.
```

You can either download and save the files to your local machine or directly to Dropbox. (Note: the latter is only required if you intend to run the program on an architecture for which no Dropbox client exists (e.g. ARM processor).)

When you run the program for the first time, it will generate a file called `app_secrets.py`. Enter your credentials in order to authenticate. If you use the Dropbox option, you have to generate a Dropbox developer [token]( https://www.dropbox.com/developers/apps).

The variable `courses = []` determines which courses will be downloaded. If you want to download files for the course `"CS999 Data Mining and Matrices"`, it is sufficient to insert `"Data Mining and Matrices"`, which will also be the download foldername for files of this course. If you enter `"CS999 Data Mining"`, the foldername will be just that and it will work as well. Be aware that if you only enter `"Data Mining"`, it may be ambiguous what to download if you are also subscribed to e.g. `"CS997 Data Mining"`.

Example:

`courses = ['Data Mining II', 'Economics']`

will produce (something like)

```
.
├── .db
├── .changelog
├── .overwritten
├── Data Mining II
│   ├── Lectures
│   ├── Tutorial
│   └── announcement.pdf
└── Economics
    ├── Lectures
    ├── Tutorial
    └── Project
```

when running the crawler. Explanations to the .folders follow below.

### Working with the Downloads

The crawler helps you with automating the tedious task of downloading lecture content. It keeps track of what has already been downloaded and only saves the most recently uploaded slides that have not been downloaded yet (delta). As such, the crawler downloads every file only once. This is a mandatory requirement, since you may want to work with the downloaded material, i.e. take notes, mark something on a slide, rename files or delete useless files.

If you want the crawler to start over, i.e. download all files again, remove the `.db` folder, which keeps track of the file hashes. It is stored in the root folder of your lecture downloads (see configuration in `app_secrets.py`).

The `.changelog` folder logs changes from every run so you can look up what was downloaded when. With the `-l` option, it logs everything, not only downloads.

In `.overwritten` you will find all files that have been saved from being overwritten. Like this, you don't have to worry about notes getting lost because a file may be overwritten by a download in the future. (Note: This could only ever happen if you rename a file to exactly the same filename of the future download.)

## Testing

In order to run the tests, out of the `test/` directory run:

```bash
$ py.test
```

## Built With

* [Python 3.6](https://docs.python.org/3/)
* [Pipenv](https://docs.pipenv.org/)
* [Requests](http://docs.python-requests.org/en/master/) - HTTP request library
* [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML parser
* [Click](https://click.palletsprojects.com/en/7.x/) - Python CLI
* [Dropbox API v2](https://www.dropbox.com/developers/documentation/http/documentation) - Dropbox API
* [TinyDB](https://tinydb.readthedocs.io/en/latest/)

## License

This project is licensed under the MIT License - see [LICENSE.md](LICENSE.md) for details.

### Disclaimer

**Use this tool responsibly and at your own risk**. For example run it once Mo, Mi on weekdays during the semester with a cronjob (on your RaspberryPi), but **do not** spam the university's servers by executing the program too frequently. You are responsible for all consequences of your behavior.
