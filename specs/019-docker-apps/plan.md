# Implementation Plan: Docker app services

**Branch**: `019-docker-apps` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

## Summary

Add `backend` and `frontend` services to `docker-compose.yml` with thin Dockerfiles.

## Structure

```text
backend/Dockerfile
backend/.dockerignore
frontend/Dockerfile
frontend/.dockerignore
docker-compose.yml  # + backend, frontend
```
