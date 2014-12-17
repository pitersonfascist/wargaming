'use strict';

/* App Module */

var wargApp = angular.module('wargApp', [
  'ngRoute',
  /*'phonecatAnimations',*/

  'wargControllers',
  'wargFilters',
  'wargServices',
  'wargDirectives'
]);

wargApp.config(['$routeProvider',
  function($routeProvider) {
    //$routeProvider.html5Mode(true);
    $routeProvider.
      when('/', {
        templateUrl: 'partials/users-list.html',
        controller: 'UsersListCtrl'
      }).
      when('/user/:userId', {
        templateUrl: 'partials/user-details.html',
        controller: 'UserCtrl'
      }).
      otherwise({
        redirectTo: '/'
      });
  }]);
