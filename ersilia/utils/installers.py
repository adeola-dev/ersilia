import shutil
import os
import sys
import tempfile
from .conda import SimpleConda
from ..default import EOS
from .. import ErsiliaBase
from .terminal import run_command
from .versioning import Versioner


class Installer(ErsiliaBase):

    def __init__(self, check_install_log=True, config_json=None, credentials_json=None):
        ErsiliaBase.__init__(self, config_json=config_json, credentials_json=credentials_json)
        self.check_install_log = check_install_log
        self.log_file = os.path.join(EOS, ".install.log")
        self.log = None
        self.read_log()
        self.versions = Versioner()

    def write_log(self):
        if self.log is None:
            return
        with open(self.log_file, 'w') as f:
            for l in sorted(self.log):
                f.write(l+"\n")

    def update_log(self, task):
        if self.log is None:
            self.log = {task}
        self.log.update([task])
        self.write_log()

    def read_log(self):
        if not os.path.exists(self.log_file):
            return
        with open(self.log_file, "r") as f:
            self.log = []
            for l in f:
                self.log += [l.rstrip()]
        self.log = set(self.log)

    def remove_log(self):
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

    def _is_done(self, name):
        if not self.check_install_log:
            return False
        if self.log is None:
            pass
        else:
            if name in self.log:
                return True
            else:
                pass
        self.update_log(name)
        return False

    @staticmethod
    def _is_tool(name):
        return shutil.which(name) is not None

    def _get_devel_path(self):
        if self.cred is None:
            return None
        path = os.path.abspath(self.cred.LOCAL.DEVEL_PATH)
        if not os.path.exists(path):
            return None
        return path

    def conda(self):
        if self._is_done("conda"):
            return
        if self._is_tool("conda"):
            return
        run_command("pip install -y conda", quiet=True)

    def git(self):
        if self._is_done("git"):
            return
        if self._is_tool("git"):
            return
        self.conda()
        run_command("conda install -y -q git", quiet=True)

    def rdkit(self):
        if self._is_done("rdkit"):
            return
        try:
            import rdkit
            exists = True
        except ModuleNotFoundError:
            exists = False
        if exists:
            return
        run_command("conda install -c conda-forge -y -q rdkit", quiet=True)

    def config(self):
        CONFIG_FILE_NAME = "config.json"
        if self._is_done("config"):
            return
        if os.path.exists(os.path.join(EOS, CONFIG_FILE_NAME)):
            return
        os.makedirs(EOS, exist_ok=True)
        dev_path = self._get_devel_path()
        if dev_path:
            src = os.path.join(dev_path, CONFIG_FILE_NAME)
            dst = os.path.join(EOS, CONFIG_FILE_NAME)
            shutil.copyfile(src, dst)
        else:
            from .download import GitHubDownloader
            gd = GitHubDownloader(overwrite=True)
            gd.download_single("ersilia-os", "ersilia", CONFIG_FILE_NAME, os.path.join(EOS, CONFIG_FILE_NAME))

    def base_conda(self):
        if self._is_done("base_conda"):
            return
        eos_base_env = self.cfg.ENV.CONDA.EOS_BASE_ENV
        sc = SimpleConda()
        if sc.exists(eos_base_env):
            return
        tmp_folder = tempfile.mkdtemp()
        tmp_repo = os.path.join(tmp_folder, "ersilia")
        tmp_script = os.path.join(tmp_folder, "script.sh")
        dev_path = self._get_devel_path()
        if dev_path:
            shutil.copytree(dev_path, tmp_repo)
        else:
            from .download import GitHubDownloader
            gd = GitHubDownloader(overwrite=True)
            gd.clone("ersilia-os", "ersilia", tmp_repo)
        is_base = sc.is_base()
        if not is_base:
            bash_script = """
            source ${0}/etc/profile.d/conda.sh
            conda deactivate
            """.format(sc.conda_prefix(False))
        else:
            bash_script = ""
        bash_script += """
        source ${0}/etc/profile.d/conda.sh
        """.format(sc.conda_prefix(True))
        bash_script += """
        cd {0}
        conda create -n {1} python={2} -y
        conda activate {1}
        pip install -e .
        ersilia
        conda deactivate
        """.format(
            tmp_repo,
            eos_base_env,
            self.versions.python_version()
        )
        with open(tmp_script, "w") as f:
            f.write(bash_script)
        run_command("bash {0}".format(tmp_script), quiet=True)

    def server_docker(self):
        if self._is_done("server_docker"):
            return
        import tempfile
        from .docker import SimpleDocker
        docker = SimpleDocker()
        org, img, tag = self.versions.server_docker_name(as_tuple=True)
        if docker.exists(org, img, tag):
            return
        # get a copy of the repository in a temporary directory
        tmp_dir = tempfile.mkdtemp()
        tmp_dir = "/home/mduranfrigola/Desktop"
        dst = os.path.join(tmp_dir, "ersilia")
        dev_path = self._get_devel_path()
        if dev_path:
            shutil.copytree(dev_path, dst)
        else:
            from .download import GitHubDownloader
            gd = GitHubDownloader(overwrite=True)
            gd.clone("ersilia-os", "ersilia", dst)
        # write the dockerfile
        dockerfile = """
        FROM bentoml/model-server:{0}
        MAINTAINER ersilia

        ENV LC_ALL=C.UTF-8
        ENV LANG=C.UTF-8

        WORKDIR {1}

        COPY . .

        RUN pip install joblib
        RUN conda install -c conda-forge rdkit
        RUN conda install -c conda-forge biopython
        RUN pip install .
        """.format(
            self.versions.bentoml_version(),
            self.cfg.ENV.DOCKER.IMAGE_WORKDIR
        )
        path = os.path.join(dst, "Dockerfile")
        with open(path, "w") as f:
            lines = dockerfile.split("\n")
            lines = lines[1:-1]
            for l in lines:
                f.write(l[8:]+"\n")
        # build image
        docker.build(path=dst, org=org, img=img, tag=tag)


def check_dependencies():
    ins = Installer()
    ins.conda()
    ins.git()
    ins.rdkit()
    ins.config()
    ins.base_conda()
    ins.server_docker()
