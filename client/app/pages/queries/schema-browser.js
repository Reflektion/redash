// import template from './schema-browser.html';

import moment from 'moment';

import { LivePaginator } from '../../utils';
import template from './schema-browser.html';
// import queryEditor from './query-editor';

class SchemaBrowserCtrl {
  constructor($location, Title, Query) {
    const page = parseInt($location.search().page || 1, 10);

    this.defaultOptions = {};

    const self = this;

    // case '/queries/my':
    // Title.set('My Queries');
    this.resource = Query.myQueries;

   // TODO
   /* this.copyPaste = (query) => {
      query_editor().queryEditor().
    }; */

    this.getSize = () => {
      const size = 20;

      return size;
    };

    function queriesFetcher(requestedPage, itemsPerPage, paginator) {
      $location.search('page', requestedPage);

      const request = Object.assign({}, self.defaultOptions,
        { page: requestedPage, page_size: itemsPerPage });

      return self.resource(request).$promise.then((data) => {
        const rows = data.results.map((query) => {
          query.created_at = moment(query.created_at);
          query.retrieved_at = moment(query.retrieved_at);
          return query;
        });
        // console.log(rows);
        // Object.keys(rows).forEach((key) => {
        //   console.log(key);
        //   if (rows[key] !== undefined) {
        //     if (rows[key].name.search('My New Query') !== -1) {
        //       // console.log(rows[key]);
        //       rows.splice(key, 1);
        //     }
        //   }
        // });

        const filteredRows = rows.filter(query => query.name.search('My New Query') === -1);
        paginator.updateRows(filteredRows);
      });
    }

    this.paginator = new LivePaginator(queriesFetcher, { page });

    this.onRefresh = () => {
      this.paginator = new LivePaginator(queriesFetcher, { page });
    };
  }
}

const SchemaBrowser = {
//  bindings: {
  //  onRefresh: '&',
    // TODO
    // onreferesh (also schema) is still somehow linked to schema API call:
    // see query.html and view.js ... links the two
    // Is schemabrowserctrl  also linked to ../schema/ API call ?
    // No it's not - that is due to view.js
//  },
  controller: SchemaBrowserCtrl,
  template,
};

export default function (ngModule) {
  ngModule.component('schemaBrowser', SchemaBrowser);

  const route = {
    template: '<page-queries-list></page-queries-list>',
    reloadOnSearch: false,
  };

  return {
    '/queries': route,
    '/queries/my': route,
  };
}
/* function SchemaBrowserCtrl($scope) {
  'ngInject';

  this.showTable = (table) => {
    table.collapsed = !table.collapsed;
    $scope.$broadcast('vsRepeatTrigger');
  };

  this.getSize = (table) => {
    let size = 18;

    if (!table.collapsed) {
      size += 18 * table.columns.length;
    }

    return size;
  };
} */

/* const SchemaBrowser = {
  bindings: {
    schema: '<',
    onRefresh: '&',
  },
  controller: SchemaBrowserCtrl,
  template,
};

export default function (ngModule) {
  ngModule.component('schemaBrowser', SchemaBrowser);
} */
