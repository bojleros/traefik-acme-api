# traefik-acme-api
Basic api that exposes traefik certificates stored in acme.json


### How does it work

This basic service is designed to be deployed with a close proximity to the Traefik instance responsible for certificate management with dns-01 route53 validation. Due to this colocation constraint this code does not provide any ssl or auth capabilities. For that reason it is not expected to expose any ports , rather to be exposed by the colocated Traefik instance - using traefik configured auth and the very same certificates it is bound to deliver to it's clients.


# How to run it

Following example is going to cover deployment on regular operating system however it should also be possible to deploy into a multicontainer k8s pod or employ rwx k8s storage to share the secret between separate pods.

## Configure Traefik

Traefik is going to act primarly as certificate management agent.
Config configuration tree is shown below:
```
/etc/traefik/
├── cert
│   └── acme.json
├── config
│   ├── dynamic
│   │   └── dynamic.yml
│   └── traefik.yml
└── envs
```

```
# cat /etc/traefik/envs
# aws user secret that grants permission to manage TXT records in particular zone
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
AWS_HOSTED_ZONE_ID=
```

```
# traefik.yml

api:
  insecure: false
  dashboard: true

experimental:
  plugins:
    staticresponse:
      moduleName: "github.com/jdel/staticresponse"
      version: "v0.0.1"

certificatesResolvers:
  route53:
    acme:
      email: <your email hete>
      storage: /etc/traefik/cert/acme.json
      dnsChallenge:
        provider: route53
        # consider following trick
        # root domain: whatever.yourdomain
        # private domain: int.whatever.yourdomain
        # you want to generate cert for *.int.whatever.yourdomain using dns-01 validation
        # private domain is not resolved by the public internet, so you put validation records containing int.whatever.yourdomain into the public domain that hosts whatever.yourdomain
        # given your private dns is providing you with a content of private zone traefik would never find the txt records defines in a public one
        # unless we use public dns servers instead of our private ones
        resolvers:
          - 1.1.1.1:53
          - 8.8.8.8:53
        delayBeforeCheck: 0

entryPoints:
  traefik:
    # better to limit to localhost than specify api.insecure=true by mistake and leave it open
    address: "127.0.0.1:8080"
  web:
    # this only serves redirections, nothing else
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: "websecure"
          scheme: "https"
  websecure:
    address: ":443"

providers:
  file:
    directory: /etc/traefik/config/dynamic
    watch: true
  docker:
    exposedByDefault: false

log:
  level: INFO
  noColor: true
  format: json

#accessLog:
#  addInternals: true
#  format: json

metrics:
  prometheus:
    addEntryPointsLabels: true
    addRoutersLabels: true
    addServicesLabels: true
    manualRouting: true
```

```
# cat /etc/traefik/config/dynamic/dynamic.yml 
---
http:
  # routers defined here will fist use matching wildcard certificate
  # in case no matching certificate can be found traefik will creade a dedicated one
  routers:
    # expose dashboard so you can look into the configuration like civilized man
    dashboard:
      rule: "Host(`dashboard.cert-api.int.whatever.yourdomain`)"
      entryPoints:
        - "websecure"
      tls: 
        certResolver: route53
      middlewares:
        - "dashboard-auth"
        - "compress"
      service: "api@internal"

    metrics:
      # expose traefik metrics - there is a metric that exports not_valid_after for each certificate :)
      rule: "Host(`cert-api.int.whatever.yourdomain`) && PathPrefix(`/metrics`)"
      entryPoints:
        - "websecure"
      tls:
        certResolver: route53
      middlewares:
        - "compress"
      service: "prometheus@internal"

    wildcard:
      rule: "Host(`wildcard.int.whatever.yourdomain`)"
      entryPoints:
        - "websecure"
      tls:
        certResolver: route53
        domains:
          - main: "*.int.whatever.yourdomain"
            sans:
              - "int.whatever.yourdomain"
      middlewares:
        - "great-success"
      service: "noop@internal"

    wildcard_maciek:
      rule: "Host(`wildcard.maciek.int.whatever.yourdomain`)"
      entryPoints:
        - "websecure"
      tls:
        certResolver: route53
        domains:
          - main: "*.maciek.int.whatever.yourdomain"
            sans:
              - "maciek.int.whatever.yourdomain"
      middlewares:
        - "great-success"
      service: "noop@internal"


  middlewares:
    # useful middleware to always return success for domains without any backend
    great-success:
      plugin:
        staticresponse:
          StatusCode: 200
          Body: "A great success :+1 !"


    # example bcrypted auth (htpasswd -nB username)
    dashboard-auth:
      basicAuth:
        users:
          - "admin:$apr1......"

    # some content can benefit from compression
    compress:
      compress: {}
```

You can start the traefik with a systemd service (note Restart=always and RestartSec=5)
```
# systemctl cat cert_api_traefik
# /etc/systemd/system/cert_api_traefik.service
[Unit]
Description=cert_api_traefik service
After=network.target
Requires=network.target

[Service]
ExecStartPre=-/usr/bin/podman rm -f cert_api_traefik
ExecStart=/usr/bin/podman run --rm --name cert_api_traefik \
    --net host \
    --env-file /etc/traefik/envs \
    -v /etc/traefik/config:/etc/traefik/config:rw \
    -v /etc/traefik/cert:/etc/traefik/cert:rw \
    -v /var/run/docker.sock:/var/run/docker.sock:rw \
    docker.io/traefik:3.2.3 --configfile /etc/traefik/config/traefik.yml
ExecStop=/usr/bin/podman stop cert_api_traefik
ExecStopPost=-/usr/bin/podman rm -f cert_api_traefik

Type=simple
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```


## Configure traefik-acme-api

Generate auth bcrypted auth material:
```
htpasswd -nB user
```

Make sure that directory containing acme.json gets mounted into /cert
We assume that static and dynamic Traefik config is in place
Provide the output of htpasswd into the middleware config
```
podman run -it --rm  -v /etc/traefik/cert:/cert \
    --label traefik.enable=true \
    --label traefik.http.routers.traefik-acme-api.rule='Host(`cert-api.int.whatever.yourdomain`)' \
    --label traefik.http.routers.traefik-acme-api.tls=true \
    --label traefik.http.services.traefik-acme-api.loadbalancer.server.port=8080 \
    --label traefik.http.routers.traefik-acme-api.entrypoints=websecure \
    --label traefik.http.middlewares.traefik-acme-api-auth.basicauth.users='<htpasswd_output here>' \
    --label traefik.http.routers.traefik-acme-api.middlewares=traefik-acme-api-auth \
    ghcr.io/bojleros/traefik-acme-api:v0.0.2-beta.8
```

Optionally check the traefik dashboard.

Given that records A/CNAME were already correctly configured it's time to try following:
```
curl -u "user:pass" -H "Accept: application/json" -H "Content-Type: application/json" https://api.whatever.yourdomain/api/v1/certificates

```




### How to use it

Get the list of available certificates in json:
```
curl -H "Accept: application/json" -H "Content-Type: application/json" http://localhost:8080/api/v1/certificates | python -m json.tool
{
    "*.whatever.yourdomain": {
        "issuer": "CN=R10,O=Let's Encrypt,C=US",
        "not_valid_after": "Wed, 02 Apr 2025 19:47:15 GMT",
        "not_valid_after_ts": 1743623235.0,
        "not_valid_before": "Thu, 02 Jan 2025 19:47:16 GMT",
        "not_valid_before_ts": 1735847236.0,
        "serial_number": ....,
        "signature_algorithm": "sha256WithRSAEncryption",
        "subject": "CN=*.whatever.yourdomain",
        "version": "Version.v3"
    },
    ...
}
```

Get the cert and key in json and base64 encoded:
```
curl -H "Accept: application/json" -H "Content-Type: application/json" http://localhost:8080/api/v1/certificate/*.whatever.yourdomain | python -m json.tool
{
    "cert": "....",
    "key": "...."
}
```

Use extraction mode to get the keys ready for deployment:
```
curl http://localhost:8080/api/v1/certificate/*.whatever.yourdomain/crt
-----BEGIN CERTIFICATE-----
....


curl http://localhost:8080/api/v1/certificate/*.whatever.yourdomain/key
-----BEGIN RSA PRIVATE KEY-----
...
```