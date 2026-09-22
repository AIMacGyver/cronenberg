"""This module holds the base Harvester class and all its subclassess."""

import json

from cronenberg.cli.tools import (
    _open,
    cc_to_dict,
    dict_to_md,
    dict_to_xml,
    iter_filenames,
    raw_to_dict,
)
from cronenberg.complexity import (
    add_inner_blocks,
    cc_visit,
    sorted_results,
)
from cronenberg.metrics import h_visit, mi_rank, mi_visit
from cronenberg.raw import analyze


class Harvester:
    """Base class defining the interface of a Harvester object.

    A Harvester has the following lifecycle:

    1. **Initialization**: `h = Harvester(paths, config)`

    2. **Execution**: `r = h.results`. `results` holds an iterable object.
       The first time `results` is accessed, `h.run()` is called. This method
       should not be subclassed. Instead, the :meth:`gobble` method should be
       implemented.

    3. **Reporting**: :meth:`as_dict` returns one dictionary.
       :meth:`as_json` dumps that dictionary with sorted object keys.
       :meth:`as_xml` returns XML when implemented.

    This class is meant to be subclasses and cannot be used directly, since
    the methods :meth:`gobble` and :meth:`as_xml` are not implemented.
    """

    def __init__(self, paths, config):
        """Initialize the Harvester.

        *paths* is a list of paths to analyze.
        *config* is a :class:`~cronenberg.cli.Config` object holding the
        configuration values specific to the Harvester.
        """
        self.paths = paths
        self.config = config
        self._results = []

    def _iter_filenames(self):
        """A wrapper around :func:`~cronenberg.cli.tools.iter_filenames`."""
        return iter_filenames(self.paths, self.config.exclude, self.config.ignore)

    def gobble(self, fobj):
        """Subclasses must implement this method to define behavior.

        This method is called for every file to analyze. *fobj* is the file
        object. This method should return the results from the analysis,
        preferably a dictionary.
        """
        raise NotImplementedError

    def run(self):
        """Start the analysis. For every file, this method calls the
        :meth:`gobble` method. Results are yielded as tuple:
        ``(filename, analysis_results)``.
        """
        for name in self._iter_filenames():
            with _open(name) as fobj:
                try:
                    yield (name, self.gobble(fobj))
                except Exception as e:
                    yield (name, {"error": str(e)})

    @property
    def results(self):
        """This property holds the results of the analysis.

        The first time it is accessed, an iterator is returned. Its
        elements are cached into a list as it is iterated over. Therefore, if
        `results` is accessed multiple times after the first one, a list will
        be returned.
        """

        def caching_iterator(it, r):
            """An iterator that caches another iterator."""
            for t in it:
                yield t
                r.append(t)

        if self._results:
            return self._results
        return caching_iterator(self.run(), self._results)

    def as_dict(self):
        """Return analysis results as one dictionary.

        Returns:
            A mapping of each filename to its analysis record.
        """
        return dict(self.results)

    def as_json(self):
        """Format the results as JSON.

        Returns:
            JSON text for :meth:`as_dict` with object keys sorted, so two
            runs emit the same bytes.
        """
        return json.dumps(self.as_dict(), sort_keys=True)

    def as_xml(self):
        """Format the results as XML."""
        raise NotImplementedError

    def as_md(self):
        """Format the results as Markdown."""
        raise NotImplementedError


class CCHarvester(Harvester):
    """A class that analyzes Python modules' Cyclomatic Complexity."""

    def gobble(self, fobj):
        """Analyze the content of the file object."""
        r = cc_visit(fobj.read(), no_assert=self.config.no_assert)
        if self.config.show_closures:
            r = add_inner_blocks(r)
        return sorted_results(r, order=self.config.order)

    def _to_dicts(self):
        """Format the results as a dictionary of dictionaries."""
        result = {}
        for key, data in self.results:
            if "error" in data:
                result[key] = data
                continue
            values = [v for v in map(cc_to_dict, data) if self.config.min <= v["rank"] <= self.config.max]
            if values:
                result[key] = values
        return result

    def as_dict(self):
        """Return Cyclomatic Complexity results as one dictionary.

        Returns:
            A mapping of each filename to ranked blocks in analysis order, or
            to an error record.
        """
        return self._to_dicts()

    def as_xml(self):
        """Format the results as XML. This is meant to be compatible with
        Jenkin's CCM plugin. Therefore not all the fields are kept.
        """
        return dict_to_xml(self._to_dicts())

    def as_md(self):
        """Format the results as Markdown."""
        return dict_to_md(self._to_dicts())


class RawHarvester(Harvester):
    """A class that analyzes Python modules' raw metrics."""

    def gobble(self, fobj):
        """Analyze the content of the file object."""
        return raw_to_dict(analyze(fobj.read()))

    def as_dict(self):
        """Return raw metrics as one dictionary.

        Returns:
            A mapping of each filename to its raw metric record. Summary
            totals are not included.
        """
        return dict(self.results)

    def as_xml(self):
        """Placeholder method. Currently not implemented."""
        raise NotImplementedError("RawHarvester: cannot export results as XML")


class MIHarvester(Harvester):
    """A class that analyzes Python modules' Maintainability Index."""

    def gobble(self, fobj):
        """Analyze the content of the file object."""
        mi = mi_visit(fobj.read(), self.config.multi)
        rank = mi_rank(mi)
        return {"mi": mi, "rank": rank}

    @property
    def filtered_results(self):
        """Filter results with respect with their rank."""
        for key, value in self.results:
            if "error" in value or self.config.min <= value["rank"] <= self.config.max:
                yield (key, value)

    def as_dict(self):
        """Return Maintainability Index results as one dictionary.

        Returns:
            A mapping of each filename whose rank is inside the configured
            range to its MI record. Error records are always included.
        """
        return dict(self.filtered_results)

    def as_xml(self):
        """Placeholder method. Currently not implemented."""
        raise NotImplementedError("Cannot export results as XML")


class HCHarvester(Harvester):
    """Computes the Halstead Complexity of Python modules."""

    def gobble(self, fobj):
        """Analyze the content of the file object."""
        code = fobj.read()
        return h_visit(code)

    def as_dict(self):
        """Return Halstead results as one dictionary.

        Returns:
            A mapping of each filename to module and function Halstead
            records, or to an error record.
        """
        return self._to_dicts()

    def _to_dicts(self):
        """Format the results as a dictionary of dictionaries."""
        result = {}
        for filename, results in self.results:
            if "error" in results:
                result[filename] = results
            else:
                result[filename] = {}
                for k, v in results._asdict().items():
                    if k == "functions":
                        result[filename]["functions"] = {key: val._asdict() for key, val in v}
                    else:
                        result[filename][k] = v._asdict()

        return result
