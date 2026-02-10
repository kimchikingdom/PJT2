# TEST RESULTS

- Generated at: 2026-02-10 12:58:46 KST
- Base URL: http://localhost:8080

## 1. Service Status

`docker compose ps --format json`:

```json
{"Command":"\"docker-entrypoint.s…\"","CreatedAt":"2026-02-10 10:40:01 +0900 KST","ExitCode":0,"Health":"","ID":"a05c4a821964","Image":"mariadb:11.4","Labels":"com.docker.compose.image=sha256:5224add29d506574e9f64e47a5023dfb4e5f28cea2011e3a938dc7be2fd55ee1,com.docker.compose.oneoff=False,com.docker.compose.version=2.40.2,org.opencontainers.image.documentation=https://hub.docker.com/_/mariadb/,org.opencontainers.image.source=https://github.com/MariaDB/mariadb-docker,org.opencontainers.image.version=11.4.10,com.docker.compose.config-hash=576445ac38e6b0bcb55cd26b15a60bf5ea09507762d341e4ce42cf352be50ed1,com.docker.compose.container-number=1,com.docker.compose.project=pjt2,com.docker.compose.project.working_dir=/Users/sangwoolee/PJT2,com.docker.compose.service=db,org.opencontainers.image.ref.name=ubuntu,org.opencontainers.image.url=https://github.com/MariaDB/mariadb-docker,desktop.docker.io/ports.scheme=v2,org.opencontainers.image.authors=MariaDB Community,org.opencontainers.image.base.name=docker.io/library/ubuntu:noble,org.opencontainers.image.licenses=GPL-2.0,org.opencontainers.image.title=MariaDB Database,com.docker.compose.project.config_files=/Users/sangwoolee/PJT2/docker-compose.yml,org.opencontainers.image.description=MariaDB Database for relational SQL,org.opencontainers.image.vendor=MariaDB Community,com.docker.compose.depends_on=","LocalVolumes":"1","Mounts":"pjt2_db_data","Name":"public-health-db","Names":"public-health-db","Networks":"pjt2_app_net","Ports":"3306/tcp","Project":"pjt2","Publishers":[{"URL":"","TargetPort":3306,"PublishedPort":0,"Protocol":"tcp"}],"RunningFor":"2 hours ago","Service":"db","Size":"0B","State":"running","Status":"Up 2 hours"}
{"Command":"\"sh -c 'flask --app …\"","CreatedAt":"2026-02-10 12:56:41 +0900 KST","ExitCode":0,"Health":"","ID":"f5aef19bee89","Image":"pjt2-was","Labels":"com.docker.compose.config-hash=2d3a89e03072d55e27ce603aecd4cdb6ea477172d93aa599f6de781a0579facf,com.docker.compose.container-number=1,com.docker.compose.image=sha256:8118f46a4541872d134ec0b13a7d27624f7ce6975af6ee1cca388b885e55e0b8,com.docker.compose.project=pjt2,com.docker.compose.service=was,com.docker.compose.depends_on=db:service_started:false,com.docker.compose.oneoff=False,com.docker.compose.project.config_files=/Users/sangwoolee/PJT2/docker-compose.yml,com.docker.compose.project.working_dir=/Users/sangwoolee/PJT2,com.docker.compose.replace=public-health-was,com.docker.compose.version=2.40.2,desktop.docker.io/ports.scheme=v2","LocalVolumes":"0","Mounts":"","Name":"public-health-was","Names":"public-health-was","Networks":"pjt2_app_net","Ports":"","Project":"pjt2","Publishers":[],"RunningFor":"2 minutes ago","Service":"was","Size":"0B","State":"running","Status":"Up 2 minutes"}
{"Command":"\"/docker-entrypoint.…\"","CreatedAt":"2026-02-10 10:40:01 +0900 KST","ExitCode":0,"Health":"","ID":"3d893037c64e","Image":"nginx:1.27-alpine","Labels":"desktop.docker.io/binds/0/Target=/etc/nginx/conf.d/default.conf,desktop.docker.io/ports/80/tcp=:8080,com.docker.compose.config-hash=0026af7e886c7cf4900091fa543d52f11617801a00fe5b4178c9a4016d5e3c64,com.docker.compose.container-number=1,com.docker.compose.project=pjt2,com.docker.compose.service=web,com.docker.compose.version=2.40.2,desktop.docker.io/binds/0/Source=/Users/sangwoolee/PJT2/web/nginx.conf,desktop.docker.io/binds/0/SourceKind=hostFile,com.docker.compose.oneoff=False,com.docker.compose.depends_on=was:service_started:false,com.docker.compose.project.working_dir=/Users/sangwoolee/PJT2,desktop.docker.io/ports.scheme=v2,maintainer=NGINX Docker Maintainers \u003cdocker-maint@nginx.com\u003e,com.docker.compose.image=sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10,com.docker.compose.project.config_files=/Users/sangwoolee/PJT2/docker-compose.yml","LocalVolumes":"0","Mounts":"/host_mnt/User…","Name":"public-health-web","Names":"public-health-web","Networks":"pjt2_app_net","Ports":"0.0.0.0:8080-\u003e80/tcp, [::]:8080-\u003e80/tcp","Project":"pjt2","Publishers":[{"URL":"0.0.0.0","TargetPort":80,"PublishedPort":8080,"Protocol":"tcp"},{"URL":"::","TargetPort":80,"PublishedPort":8080,"Protocol":"tcp"}],"RunningFor":"2 hours ago","Service":"web","Size":"0B","State":"running","Status":"Up 2 hours"}
```

## 2. Automated Tests (pytest)

- Exit code: 0

```text
..........                                                               [100%]
10 passed in 2.26s
```

## 3. Smoke Checks

| Check | HTTP Code |
|---|---:|
| GET / | 200 |
| GET /posts | 200 |
| GET /health-info | 200 |
| GET /health-centers | 200 |
| GET /health-programs/vaccination | 200 |
| POST /login (user1) | 302 |
| GET /admin (user1) | 302 |
| GET /notices/2 private (user1) | 302 |
| POST /login (admin) | 302 |
| GET /admin (admin) | 200 |
| GET /admin/logs (admin) | 200 |
| GET /notices/2 private (admin) | 200 |
| GET /security/scenarios (admin) | 200 |

## 4. Seed Data Snapshot

```text
users=4
posts=4
notices=2
complaints=2
logs=119
mydata=1
```

## 5. Result Summary

- pytest: PASS
- smoke critical checks: PASS (status codes captured above)
