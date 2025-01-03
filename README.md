# traefik-acme-api
Basic api that exposes traefik certificates stored in acme.json


### How does it work

This basic service is designed to be deployed with a close proximity to the Traefik instance responsible for certificate management with dns-01 route53 validation. Due to this colocation constraint this code does not provide any ssl or auth capabilities. For that reason it is not expected to expose any ports , rather to be exposed by the colocated Traefik instance - using traefik configured auth and the very same certificates it is bound to deliver to it's clients.


# How to run it

```
# make sure that directory containing acme.json gets mounted into /cert
podman run -it --rm -v test:/cert:z traefik-acme-api

```

As long as you have Traefik with the docker provider configured you can use following settings to expose api:
```
# make sure traefik is configured to serve over https only and to add some auth!
    --label traefik.enable=true \
    --label traefik.http.routers.traefik-acme-api.rule="Host(`cert-api.int.barek.org`)" \
    --label traefik.http.routers.traefik-acme-api.tls=true \
    --label traefik.http.services.traefik-acme-api.loadbalancer.server.port=8081
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