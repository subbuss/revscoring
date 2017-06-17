import mwbase

from ....datasources import Datasource
from ....dependencies import DependentSet
from .diff import Diff


class Revision(DependentSet):

    def __init__(self, name, revision_datasources):
        super().__init__(name)

        self.entity = Datasource(
            name + ".entity", _process_entity,
            depends_on=[revision_datasources.text]
        )
        """
        A `~mwbase.Entity` for the Wikibase content
        """

        self.sitelinks = Datasource(
            name + ".sitelinks", _process_sitelinks, depends_on=[self.entity]
        )
        """
        A `dict` of wiki/sitelink pairs in the revision
        """

        self.labels = Datasource(
            name + ".labels", _process_labels, depends_on=[self.entity]
        )
        """
        A `dict` of lang/label pairs in the revision
        """

        self.aliases = Datasource(
            name + ".aliases", _process_aliases, depends_on=[self.entity]
        )
        """
        A `dict` of lang_code/aliases in the revision
        """

        self.descriptions = Datasource(
            name + ".descriptions", _process_descriptions,
            depends_on=[self.entity]
        )
        """
        A `dict` of lang_code/description pairs in the revision
        """

        self.properties = Datasource(
            name + ".properties", _process_properties, depends_on=[self.entity]
        )
        """
        A `dict` of properties with statement lists in the revision
        """

        if hasattr(revision_datasources, "parent") and \
           hasattr(revision_datasources.parent, "text"):
            self.parent = Revision(
                name + ".parent",
                revision_datasources.parent
            )

            if hasattr(revision_datasources, "diff"):
                self.diff = Diff(name + ".diff", self)


def _process_entity(text):
    if text is not None:
        return mwbase.Entity.from_json(text)
    else:
        return None


def _process_labels(entity):
    return entity.labels


def _process_descriptions(entity):
    return entity.descriptions


def _process_aliases(entity):
    return entity.aliases


def _process_properties(entity):
    return entity.properties


def _process_sitelinks(entity):
    return entity.sitelinks
