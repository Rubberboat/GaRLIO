#!/usr/bin/env python3
"""Run pinned GaRLIO, a separately verified fork, and JURLIO on one sensor bag.

Requires matching, already-built Docker images. No network, privileged container,
GUI access, image rebuild or real robot connection is needed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def hashes(root, names):
    result = {}
    for name in names:
        path = root / name
        if not path.exists():
            raise RuntimeError('Missing source: ' + str(path))
        for file in sorted(path.rglob('*')) if path.is_dir() else [path]:
            if file.is_file() and '__pycache__' not in file.parts:
                result[file.relative_to(root).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jurlio-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--bag', type=Path, help='Omit to generate the deterministic synthetic room bag')
    p.add_argument('--config', type=Path)
    p.add_argument('--groundtruth', type=Path, help='TUM reference; LiDAR origin for real data')
    p.add_argument('--runs', type=int, default=3)
    p.add_argument('--methods', nargs='+', choices=['garlio', 'garlio_gpt', 'baseline', 'robust', 'dynamic'],
                   default=['garlio', 'baseline', 'robust', 'dynamic'])
    p.add_argument('--rate', type=float, default=1)
    p.add_argument('--cpus', type=int, default=2)
    p.add_argument('--memory', default='6g')
    p.add_argument('--garlio-image', default='radar-point-lio-ros:phase0-gpt')
    p.add_argument('--jurlio-image', default='jurlio:verify-gpt')
    p.add_argument('--garlio-fork-root', type=Path, default=ROOT.parent,
                   help='Exact fork snapshot used to build the image; never compared to the pinned baseline')
    p.add_argument('--garlio-fork-image', help='Defaults to --garlio-image')
    a = p.parse_args()
    if a.runs < 1 or a.rate <= 0 or not __import__('math').isfinite(a.rate) or a.cpus < 1:
        p.error('runs, rate and cpus must be positive')
    if any((a.bag, a.config, a.groundtruth)) and not all((a.bag, a.config, a.groundtruth)):
        p.error('--bag, --config and --groundtruth must be supplied together')
    jroot, out = a.jurlio_root.resolve(), a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for folder in ('logs', 'inputs'):
        (out / folder).mkdir()
    commands = []
    def execute(command, label, capture=False):
        commands.append({'label': label, 'command': command, 'started_unix': time.time()})
        print(label, flush=True)
        with (out / 'logs' / (label + '.log')).open('w') as log:
            result = subprocess.run(command, stdout=subprocess.PIPE if capture else log, stderr=log, text=True)
            if capture:
                log.write(result.stdout)
        commands[-1].update(returncode=result.returncode, finished_unix=time.time())
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        if result.returncode:
            raise RuntimeError(f'{label} failed; see {out}/logs/{label}.log')
        return result.stdout if capture else None
    images = json.loads(execute(['docker', 'image', 'inspect', a.garlio_image, a.jurlio_image, a.garlio_fork_image or a.garlio_image], 'images', True))
    (out / 'images.json').write_text(json.dumps(images, indent=2) + '\n')
    # Resolve tags to immutable IDs once, so another build cannot change a run.
    gid, jid, fid = [image['Id'] for image in images]
    base = ['docker', 'run', '--rm', '--init', '--network', 'none', '--user', f'{os.getuid()}:{os.getgid()}',
            '--cpus', str(a.cpus), '--memory', a.memory, '-e', 'HOME=/tmp/simulation-home',
            '-e', 'PYTHONDONTWRITEBYTECODE=1',
            '-v', f'{ROOT}:/work:ro', '-v', f'{jroot}:/jurlio:ro', '-v', f'{out}:/results',
            '-v', f'{a.garlio_fork_root.resolve()}:/garlio-fork:ro']
    bag_path = '/results/inputs/synthetic.bag'
    if a.bag:
        base += ['-v', f'{a.bag.resolve()}:/data/input.bag:ro']
        bag_path = '/data/input.bag'
    def container(image, *command, fork=False):
        variant = ['-e', 'RESEARCH_GARLIO_VARIANT=' + ('fork' if fork else 'baseline'),
                   '-e', 'RESEARCH_FORK_SOURCE=/garlio-fork']
        return base + variant + [image, 'bash', '-c',
            'mkdir -p "$HOME"; git config --global --add safe.directory /opt/research/catkin_ws/src/garlio; exec "$@"',
            'simulation', *command]
    source = {'garlio_fork': hashes(a.garlio_fork_root.resolve(), ('CMakeLists.txt', 'package.xml', 'LICENSE', 'src', 'include', 'config', 'launch', 'rviz_cfg')),
              'jurlio': hashes(jroot, ('CMakeLists.txt', 'package.xml', 'src', 'include')),
              'jurlio_tools': hashes(jroot, ('scripts', 'tests/synthetic.yaml')),
              'garlio_tools': hashes(ROOT, ('scripts', 'launch'))}
    (out / 'source_hashes.json').write_text(json.dumps(source, indent=2) + '\n')
    check = '''import hashlib,json,pathlib,sys
expected=json.loads(pathlib.Path('/results/source_hashes.json').read_text())[sys.argv[1]]
root=pathlib.Path(sys.argv[2])
wrong=[name for name,digest in expected.items() if not (root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest]
if wrong: raise SystemExit('Stale/different binary source snapshot: '+str(wrong))
print('Verified',len(expected),'build source files')'''
    # The local fork is allowed to differ from the upstream baseline. Verify the
    # latter against its image lock/SHA/clean state, and the fork against its
    # complete build manifest plus the explicitly selected source snapshot.
    verify = "import sys,json;sys.path.insert(0,'/work/scripts');from garlio_source import runtime_source;print(json.dumps(runtime_source(sys.argv[1])))"
    if 'garlio' in a.methods:
        execute(container(gid, 'python3', '-c', verify, 'garlio'), 'verify_garlio')
    if 'garlio_gpt' in a.methods:
        execute(container(fid, 'python3', '-c', verify, 'garlio_gpt', fork=True), 'verify_garlio_fork')
    execute(container(jid, 'python3', '-c', check, 'jurlio', '/ws/src/jurlio'), 'verify_jurlio')
    execute(container(gid, 'python3', '-m', 'unittest', 'discover', '-s', '/work/tests', '-v'), 'garlio_harness_tests')
    execute(container(jid, 'python3', '-m', 'unittest', 'discover', '-s', '/jurlio/tests', '-v'), 'jurlio_tests')
    if a.bag:
        shutil.copyfile(a.config, out / 'inputs/config.yaml')
        shutil.copyfile(a.groundtruth, out / 'inputs/groundtruth.tum')
    else:
        shutil.copyfile(jroot / 'tests/synthetic.yaml', out / 'inputs/config.yaml')
        shutil.copyfile(jroot / 'scripts/make_synthetic_bag.py', out / 'inputs/make_synthetic_bag.py')
        execute(container(jid, 'python3', '/results/inputs/make_synthetic_bag.py', bag_path), 'generate_bag')
    from run_experiment import digest
    bag_source = a.bag.resolve() if a.bag else out / 'inputs/synthetic.bag'
    (out / 'experiment.json').write_text(json.dumps(dict(
        input_kind='real' if a.bag else 'synthetic', bag=str(bag_source), bag_sha256=digest(bag_source),
        cpus=a.cpus, memory=a.memory, rate=a.rate, repeats=a.runs,
        alignment='se3' if a.bag else 'none',
        estimated_origin='IMU', evaluation_origin='LiDAR' if a.bag else 'coincident IMU/LiDAR',
        garlio_image=gid, garlio_fork_image=fid, jurlio_image=jid), indent=2) + '\n')
    for source_root, label in [(ROOT, 'garlio_harness'), (jroot, 'jurlio')]:
        for folder in ('scripts', 'launch'):
            shutil.copytree(source_root / folder, out / 'source_snapshot' / label / folder, ignore=shutil.ignore_patterns('__pycache__'))
    # Alternate GaRLIO/JURLIO order across repeats; never run estimators concurrently.
    statuses = []
    for repeat in range(1, a.runs + 1):
        methods = list(dict.fromkeys(a.methods))
        if repeat % 2 == 0:
            methods.reverse()
        for method in methods:
            label = f'{method}_{repeat}'
            try:
                if method in ('garlio', 'garlio_gpt'):
                    command = container(fid if method == 'garlio_gpt' else gid, 'python3', '/work/scripts/run_experiment.py', method, 'sequence',
                        '--bag', bag_path, '--config', '/results/inputs/config.yaml',
                        '--output', f'/results/repeat_{repeat}', '--runs', '1', '--rate', str(a.rate), fork=method == 'garlio_gpt')
                    target = f'/results/repeat_{repeat}/{method}/sequence/run_1'
                else:
                    target = f'/results/repeat_{repeat}/jurlio_{method}'
                    command = container(jid, 'python3', '/jurlio/scripts/run_replay.py', bag_path,
                        '--config', '/results/inputs/config.yaml', '--output', target, '--mode', method, '--rate', str(a.rate))
                execute(command, label)
                evaluation = ['python3', '/jurlio/scripts/evaluate.py', target + '/trajectory.tum',
                    '/results/inputs/groundtruth.tum', '--align', 'se3' if a.bag else 'none', '--output', target + '/metrics.json']
                if a.bag:
                    evaluation += ['--estimate-to-lidar', '/results/inputs/config.yaml']
                execute(container(jid, *evaluation), label + '_metrics')
                statuses.append({'method': method, 'repeat': repeat, 'status': 'completed', 'directory': target.removeprefix('/results/')})
            except RuntimeError as error:
                print(str(error), file=sys.stderr, flush=True)
                statuses.append({'method': method, 'repeat': repeat, 'status': 'failed', 'error': str(error),
                                 'directory': target.removeprefix('/results/')})
            (out / 'status.json').write_text(json.dumps(statuses, indent=2) + '\n')
    if any(row['status'] != 'completed' for row in statuses):
        raise SystemExit('Some runs failed; preserved all evidence in ' + str(out))
    print('Completed all comparisons: ' + str(out))


if __name__ == '__main__':
    main()
