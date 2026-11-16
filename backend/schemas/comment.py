from marshmallow import Schema, fields
from schemas.user import AdminIdSecurityMixin, UserPublicSchema
class CommentSchema(Schema,AdminIdSecurityMixin):
    id = fields.Str(dump_only=True)
    content = fields.Str(required=True)
    role = fields.Str(attribute="author.role", dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    score = fields.Int(dump_only=True)
    author_id = fields.Str(attribute="user_id", dump_only=True)
    author_username = fields.Str(attribute="author.username", dump_only=True)
    author = fields.Nested(UserPublicSchema(), dump_only=True)
    # This reaches into the 'author' relationship in the Model 
    # and pulls only the 'username'
    username = fields.String(attribute="author.username", dump_only=True)
