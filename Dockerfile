# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

ARG TARGETARCH
ARG VIAM_CHANNEL=stable

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl libfuse2 \
    && rm -rf /var/lib/apt/lists/* \
    && case "$TARGETARCH" in \
         amd64) viam_arch=x86_64 ;; \
         arm64) viam_arch=aarch64 ;; \
         *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
       esac \
    && curl --fail --location --retry 3 \
       "https://storage.googleapis.com/packages.viam.com/apps/viam-server/viam-server-${VIAM_CHANNEL}-${viam_arch}.AppImage" \
       --output /usr/local/bin/viam-server \
    && chmod 0755 /usr/local/bin/viam-server

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY bin ./bin
RUN python -m pip install --no-cache-dir '.[bridge]' \
    && chmod 0755 /app/bin/run-module

ENV APPIMAGE_EXTRACT_AND_RUN=1 \
    VIAM_HOME=/var/lib/viam

VOLUME ["/var/lib/viam"]
EXPOSE 8080 8081

ENTRYPOINT ["viam-server"]
CMD ["-config", "/config/viam.json", "-no-tls"]
