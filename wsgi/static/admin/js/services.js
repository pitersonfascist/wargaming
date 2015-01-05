'use strict';

/* Services */

var wargServices = angular.module('wargServices', ['ngResource']);

wargServices.factory('Account', ['$resource',
  function($resource){
    return $resource('/api/user', {}, {
      query: {method:'GET', params:{}, isArray:false}
    });
  }]);

wargServices.factory('REGISTEREDUSER', 
  function(){
    var user;
    // public API
    return {
      getData: function () { return user; },
      setData: function ( value ) { user = value; }
    };
  });

wargServices.factory('Logout', ['$resource',
  function($resource){
    return $resource('/api/user/logout', {}, {
      query: {method:'GET', params:{}, isArray:false}
    });
  }]);

wargServices.factory('User', ['$resource',
  function($resource){
    return $resource('/api/user/:userId', {}, {
      query: {method:'GET', params:{userId:0}, isArray:false}
    });
  }]);

wargServices.factory('Users', ['$resource',
  function($resource){
    return $resource('/api/user:action', {}, {
      query: {method:'GET', params:{action: "/search", q: "", offset: 0, count: 20}, isArray:true},
      online: {method:'GET', params:{action: "s/online"}, isArray:true}
    });
  }]);

wargServices.factory('Stats', ['$resource',
  function($resource){
    return $resource('/api/system/info', {}, {
      query: {method:'GET', params:{}, isArray:false}
    });
  }]);