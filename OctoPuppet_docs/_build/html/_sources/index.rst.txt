.. OctoPuppet documentation master file, created by
   sphinx-quickstart on Sun Oct 11 21:19:32 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to OctoPuppet's documentation!
======================================

.. image:: OctoPrintlabel.png


Introduction to OctoPuppet
^^^^^^^^^^^^^^^^^^^^^^^^^^

OctoPuppet is an OctoPrint-based web interface for controlling 3D printers.
OctoPuppet relies heavily on the original OctoPrint, incorporating changes and features to better meet the institutional needs of libraries, makerspaces,
and FabLabs with large user bases, multiple printers, and where prints need to be tracked on per-user basis.
OctoPuppet uses FabApp (a separate project developed in the UTA FabLab; the source will be released publicly soon) as the backend
to track users’ prints while keeping the many cool features of OctoPrint intact.

.. image:: octoprint-logo.png
   :align: right

OctoPrint provides a snappy web interface for controlling consumer 3D printers. It is Free Software and released under the
`GNU Affero General Public License V3 <http://www.gnu.org/licenses/agpl-3.0.html>`_ .


Its website can be found at `octoprint.org <https://octoprint.org/?utm_source=github&utm_medium=readme>`_.

The community forum is available at `community.octoprint.org <https://community.octoprint.org/?utm_source=github&utm_medium=readme>`_.

The FAQ can be accessed by following `faq.octoprint.org <https://community.octoprint.org/c/support/faq/14>`_.

The official plugin repository can be reached at `plugins.octoprint.org <https://plugins.octoprint.org/>`_.

.. important::

   OctoPrint’s development wouldn’t be possible without the `financial support by its community <https://octoprint.org/support-octoprint/>`_.
   If you enjoy OctoPrint, please consider becoming a regular supporter!

.. image:: sourcecoderepo.png


You are currently looking at the source code repository of OctoPrint.
If you already installed it (e.g. by using the Raspberry Pi targeted distribution `OctoPi <https://github.com/guysoft/OctoPi>`_ ) and only want to find out how to use it,
`the official documentation <https://docs.octoprint.org/en/master/>`_
might be of more interest for you. You might also want to subscribe to join `the community forum at community.octoprint.org <https://community.octoprint.org/>`_ 
where there are other active users who might be able to help you with any questions you might have.




.. toctree::
   :maxdepth: 2
   :caption: Code documentation:

   storage.py <storage.rst>
