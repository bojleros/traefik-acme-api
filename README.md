# traefik-acme-api
Basic api that exposes traefik certificates stored in acme.json


### How does it work

This basic service is designed to be deployed with a close proximity to the Traefik instance responsible for certificate management with dns-01 route53 validation. Due to this colocation constraint this code does not provide any ssl or auth capabilities. For that reason it is not expected to expose any ports , rather to be exposed by the colocated Traefik instance - using traefik configured auth and the very same certificates it is bound to deliver to it's clients.


# How to run it

```
#generate auth bcrypted auth material
htpasswd -nB admin


# make sure that directory containing acme.json gets mounted into /cert
# we assume that static and dynamic Traefik config is in place
podman run -it --rm \
-e GUNICORN_CMD_ARGS="--bind 0.0.0.0:8081 --access-logfile - --error-logfile -" \
-v /etc/traefik/cert:/cert \
--label traefik.enable=true \
--label traefik.http.routers.traefik-acme-api.rule='Host(`api.whatever.yourdomain`)' \
--label traefik.http.routers.traefik-acme-api.tls=true \
--label traefik.http.services.traefik-acme-api.loadbalancer.server.port=8081 \
--label traefik.http.routers.traefik-acme-api.entrypoints=websecure \
--label traefik.http.middlewares.traefik-acme-api.basicauth.users='htpaswd output material here' \
--label traefik.http.routers.traefik-acme-api.middlewares=traefik-acme-api \
ghcr.io/bojleros/traefik-acme-api:v0.0.2-beta.0


# try
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