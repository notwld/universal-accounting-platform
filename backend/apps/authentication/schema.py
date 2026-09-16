from drf_spectacular.extensions import OpenApiAuthenticationExtension


class ClerkJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.authentication.authenticators.clerk.ClerkJWTAuthentication"
    name = "ClerkBearer"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Clerk session JWT",
        }
